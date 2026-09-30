import datetime
from app.models import ReportSubmission, User, user_template_access
from app.extensions import db

class TemplateService:
    @staticmethod
    def complete_template(template):
        """
        Завершает сбор отчета и автоматически снимает все статусы «На доработке»,
        возвращая их в первоначальное сданное состояние.
        """
        template.is_completed = True
        db.session.query(ReportSubmission).filter_by(template_id=template.id, is_revision=True).update({
            'is_revision': False,
            'revision_comment': None,
            'returned_at': None,
            'returned_by_id': None
        }, synchronize_session='fetch')

    @staticmethod
    def get_dashboard_stats(all_templates):
        """
        Вычисляет статистику по шаблонам (должники, распределение по статусам).
        Использует оптимизированные запросы (решает проблему N+1).
        """
        needs_commit = False
        template_ids = [t.id for t in all_templates]
        if not template_ids:
            return {}, {}, [], [], [], [], [], []

        # 1. Загружаем сразу всех назначенных пользователей для нужных шаблонов
        assigned_users_raw = db.session.query(
            user_template_access.c.template_id, User
        ).join(User, user_template_access.c.user_id == User.id)\
         .filter(user_template_access.c.template_id.in_(template_ids)).all()
        
        assigned_users_map = {t_id: [] for t_id in template_ids}
        for t_id, user in assigned_users_raw:
            if t_id in assigned_users_map:
                assigned_users_map[t_id].append(user)

        # 2. Загружаем все сданные отчеты для этих шаблонов (разделяем принятые и на доработке)
        submissions_raw = db.session.query(
            ReportSubmission.template_id,
            ReportSubmission.user_id,
            ReportSubmission.is_revision
        ).filter(ReportSubmission.template_id.in_(template_ids)).all()
        
        submitted_user_ids_map = {t_id: set() for t_id in template_ids}
        for t_id, user_id, is_revision in submissions_raw:
            if not is_revision:
                submitted_user_ids_map[t_id].add(user_id)

        # 3. Загружаем данные по отчетам на доработке
        revisions_raw = db.session.query(
            ReportSubmission.template_id,
            ReportSubmission.user_id,
            ReportSubmission.revision_comment,
            ReportSubmission.returned_at,
            User
        ).join(User, ReportSubmission.user_id == User.id)\
         .filter(ReportSubmission.template_id.in_(template_ids), ReportSubmission.is_revision == True).all()
        
        revisions_map = {t_id: [] for t_id in template_ids}
        for t_id, user_id, comment, returned_at, user in revisions_raw:
            if t_id in revisions_map:
                revisions_map[t_id].append({
                    'user': user,
                    'comment': comment or '',
                    'returned_at': returned_at
                })

        pure_templates = []
        published_templates = []
        revision_templates = []
        draft_templates = []
        archived_templates = []
        completed_templates = []
        debtors_map = {}

        for t in all_templates:
            # Автоматическое закрытие отчетов с истекшим сроком
            if not t.is_completed and t.is_published and t.deadline and datetime.date.today() > t.deadline:
                TemplateService.complete_template(t)
                # Обновляем in-memory словари, так как БД обновилась, 
                # но текущий цикл всё еще использует старые данные
                for rev_item in revisions_map.get(t.id, []):
                    submitted_user_ids_map[t.id].add(rev_item['user'].id)
                revisions_map[t.id] = []
                needs_commit = True
                
            assigned_users = assigned_users_map.get(t.id, [])
            submitted_user_ids = submitted_user_ids_map.get(t.id, set())
            rev_items = revisions_map.get(t.id, [])
            
            # Должники = Назначенные минус успешно сдавшие
            debtors = [u for u in assigned_users if u.id not in submitted_user_ids]
            debtors_map[t.id] = debtors
            
            if t.is_archived:
                archived_templates.append(t)
            elif t.is_template:
                pure_templates.append(t)
            elif not t.is_published:
                draft_templates.append(t)
            else:
                has_active_revisions = len(rev_items) > 0
                if has_active_revisions:
                    revision_templates.append(t)

                if (t.is_completed or (len(assigned_users) > 0 and len(debtors) == 0)) and not has_active_revisions:
                    completed_templates.append(t)
                else:
                    published_templates.append(t)
                    
        if needs_commit:
            db.session.commit()

        return debtors_map, revisions_map, pure_templates, published_templates, revision_templates, draft_templates, archived_templates, completed_templates

    @staticmethod
    def sort_templates(templates, sort_by):
        """Сортировка списка шаблонов по параметру."""
        if sort_by == 'deadline_asc':
            return sorted(templates, key=lambda x: x.deadline or datetime.date.max)
        elif sort_by == 'deadline_desc':
            return sorted(templates, key=lambda x: x.deadline or datetime.date.min, reverse=True)
        elif sort_by == 'name_asc':
            return sorted(templates, key=lambda x: x.name.lower())
        elif sort_by == 'name_desc':
            return sorted(templates, key=lambda x: x.name.lower(), reverse=True)
        elif sort_by == 'id_desc':
            return sorted(templates, key=lambda x: x.id, reverse=True)
        return sorted(templates, key=lambda x: x.deadline or datetime.date.max)

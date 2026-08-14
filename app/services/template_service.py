import datetime
from app.models import ReportSubmission, User, user_template_access
from app import db

class TemplateService:
    @staticmethod
    def get_dashboard_stats(all_templates):
        """
        Вычисляет статистику по шаблонам (должники, распределение по статусам).
        Использует оптимизированные запросы (решает проблему N+1).
        """
        needs_commit = False
        template_ids = [t.id for t in all_templates]
        if not template_ids:
            return {}, [], [], [], [], []

        # 1. Загружаем сразу всех назначенных пользователей для всех шаблонов
        assigned_users_raw = db.session.query(
            user_template_access.c.template_id, User
        ).join(User, user_template_access.c.user_id == User.id).all()
        
        assigned_users_map = {t_id: [] for t_id in template_ids}
        for t_id, user in assigned_users_raw:
            assigned_users_map[t_id].append(user)

        # 2. Загружаем все сданные отчеты для этих шаблонов
        submissions_raw = db.session.query(
            ReportSubmission.template_id, ReportSubmission.user_id
        ).filter(ReportSubmission.template_id.in_(template_ids)).all()
        
        submitted_user_ids_map = {t_id: set() for t_id in template_ids}
        for t_id, user_id in submissions_raw:
            submitted_user_ids_map[t_id].add(user_id)

        pure_templates = []
        published_templates = []
        draft_templates = []
        archived_templates = []
        completed_templates = []
        debtors_map = {}

        for t in all_templates:
            # Автоматическое закрытие отчетов с истекшим сроком
            if not t.is_completed and t.is_published and t.deadline and datetime.date.today() > t.deadline:
                t.is_completed = True
                needs_commit = True
                
            assigned_users = assigned_users_map.get(t.id, [])
            submitted_user_ids = submitted_user_ids_map.get(t.id, set())
            
            # Должники = Назначенные минус Сдавшие
            debtors = [u for u in assigned_users if u.id not in submitted_user_ids]
            debtors_map[t.id] = debtors
            
            # Временно добавляем атрибуты к объекту шаблона, чтобы не переписывать Jinja шаблоны, 
            # которые могут обращаться к t.assigned_users, вызывая ленивый запрос.
            # Если Jinja вызывает t.assigned_users, она выполнит запрос. Поэтому мы должны быть осторожны.
            
            if t.is_archived:
                archived_templates.append(t)
            elif t.is_template:
                pure_templates.append(t)
            elif not t.is_published:
                draft_templates.append(t)
            else:
                if t.is_completed or (len(assigned_users) > 0 and len(debtors) == 0):
                    completed_templates.append(t)
                else:
                    published_templates.append(t)
                    
        if needs_commit:
            db.session.commit()

        return debtors_map, pure_templates, published_templates, draft_templates, archived_templates, completed_templates

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

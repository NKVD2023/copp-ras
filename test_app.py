from app import create_app
app = create_app()
app.testing = True
client = app.test_client()
response = client.get('/', follow_redirects=True)
print(response.status_code)
if response.status_code == 500:
    print(response.data.decode('utf-8'))

from dotenv import dotenv_values
values = dotenv_values('.env')
for key, value in values.items():
    if key.startswith('ADMIN'):
        print(key, value)

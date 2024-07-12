from flask import Flask

app = Flask(__name__)
host = '0.0.0.0'
port = 5000
service_name = 'application'

@app.route('/hello/<user>')
def hello(user: str):
    return (f'Hello from {service_name}, {user}')

if __name__ == "__main__":
    app.run(host=host, port=port)
    
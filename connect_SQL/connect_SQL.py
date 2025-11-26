from sqlalchemy import create_engine
import json
import os

def connect_sql():

    config_path = "D:/Chatbot_Data4Life/v1/connect_SQL/config.json"

    with open(config_path, "r") as f:
        config = json.load(f)

    DB_SERVER = config["connection"]["server"]
    DB_DATABASE = config["connection"]["database"]
    DB_USERNAME = config["connection"]["username"]
    DB_PASSWORD = config["connection"]["password"]
    ODBC_DRIVER = "ODBC Driver 17 for SQL Server"

    CONNECTION_STRING = (
        f"mssql+pyodbc://{DB_USERNAME}:{DB_PASSWORD}@{DB_SERVER}/{DB_DATABASE}"
        f"?driver={ODBC_DRIVER.replace(' ', '+')}"
    )


    try:
        engine = create_engine(CONNECTION_STRING)
        with engine.connect() as connection:
            print("Kết nối tới SQL Server thành công!")
        return engine
    except Exception as e:
        print(f"Lỗi kết nối CSDL: {e}")
        print("Vui lòng kiểm tra lại thông tin trong CONNECTION_STRING.")
        return None


from pathlib import Path
import subprocess
from pymysql import Connection
import platform
from dotenv import load_dotenv
import os


load_dotenv()

class Database:
 
    @staticmethod
    def init_connection():
        try:
            Database.con = Connection(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT")),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWD"),
                database=os.getenv("DB_DATABASE")
            )
        except Exception as e:
            print(f"\033[31mError initializing database connection: {e}\033[0m")
            raise

    @staticmethod
    def sql_sentence_commit(sentence: str, params=None):
        try:
            if not hasattr(Database, 'con'):
                raise Exception("\033[31mDatabase connection not initialized\033[0m")

            with Database.con.cursor() as cursor:
                if params:
                    cursor.execute(sentence, params)
                else:
                    cursor.execute(sentence)
                Database.con.commit()
        except Exception as e:
            print(f"\033[31mError executing SQL statement: {e}\033[0m")
            raise

    @staticmethod
    def close_connection():
        try:
            if hasattr(Database, 'con'):
                Database.con.close()
                delattr(Database, 'con')
        except Exception as e:
            print(f"\033[31mError closing database connection: {e}\033[0m")
            raise


class CmdHandler:

    @staticmethod
    def __run(command: str | list[str]):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip()
        except Exception as e:  
            print(f"\033[31mError executing command '{command}': {e}\033[0m")
            return "", str(e)

    @staticmethod
    def get_local_image_info():
        try:
            if platform.system() == "Windows":
                out, err = CmdHandler.__run("docker images")
            elif platform.system() == "Linux":
                out, err = CmdHandler.__run("sudo docker images")
            else:
                print(f"\033[31mUnsupported operating system: {platform.system()}\033[0m")
                return []

            if err:
                print(f"\033[31mError fetching images: {err}\033[0m")
                return []
        
            print(out)
            info_lst: list = []
            for line in out.splitlines()[1:]:
                cols = line.split()
                if len(cols) >= 4:   
                    repository = cols[0]  
                    tag = cols[1]   
                    image_id = cols[2]  
                    size = cols[-1]       
                    info_lst.append((repository, tag, image_id, size))

            return info_lst
        
        except Exception as e:
            print(f"\033[31mError processing image info: {e}\033[0m")
            return []

    @staticmethod
    def update_info_to_db():
        pass

    @classmethod
    def pull_images_from_database():
        pass

    @staticmethod
    def export_image_tar():
        pass


if __name__ == "__main__": 
    # Database.init_connection()

    # Database.sql_sentence_commit("""
    #         CREATE TABLE IF NOT EXISTS images (
    #             id INT PRIMARY KEY AUTO_INCREMENT,
    #             repository VARCHAR(255) NOT NULL,
    #             tag VARCHAR(100) NOT NULL,
    #             hash VARCHAR(100) NOT NULL,
    #             size VARCHAR(50) NOT NULL
    #         );
    # """)
 
    # Database.close_connection()

    l = CmdHandler.get_local_image_info()
    print(l)
from pathlib import Path
import subprocess
from pymysql import Connection
import platform
from dotenv import load_dotenv
import os
import json
from abc import ABC, abstractmethod

load_dotenv()

class Db_Interface(ABC):

    @staticmethod
    @abstractmethod
    def init_connection():
        # Initialize the database connection
        pass

    @staticmethod
    @abstractmethod
    def sql_sentence_commit(sentence: str, params=None):
        # Execute a SQL statement with commit
        pass
 
    @staticmethod
    @abstractmethod
    def close_connection():
        # Close the database connection
        pass


class Cmd_interface(ABC):
    @staticmethod
    @abstractmethod
    def __run(command: str | list[str]):
        # Run a shell command
        pass

    @staticmethod
    @abstractmethod
    def get_local_image_info(if_print: bool):
        # Get information about local Docker images
        pass

    @staticmethod
    @abstractmethod
    def update_info_to_db():
        # Update Docker image information in the database
        pass

    @staticmethod
    @abstractmethod
    def get_db_image_info():
        # Get information about Docker images from the database
        pass

    @staticmethod
    @abstractmethod
    def get_file_image_info(filepath: str):
        # Get imformation from a images.json file
        pass

    @staticmethod
    @abstractmethod
    def pull_images_from_database():
        # Pull all Docker images from the database information
        pass

    @staticmethod
    @abstractmethod
    def export_local_image_file():
        # Export all Docker image simple info to a images.json file
        pass

    @staticmethod
    @abstractmethod
    def export_local_image_tar():
        # Export all Docker image to each tar file
        pass

##############################################################################

class Database(Db_Interface):

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


class CmdHandler(Cmd_interface):

    @staticmethod
    def __run(command: str | list[str]):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip()
        except Exception as e:  
            print(f"\033[31mError executing command '{command}': {e}\033[0m")
            return "", str(e)

    @staticmethod
    def get_local_image_info(if_print: bool = True):
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

            if if_print:
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
        try:
            Database.init_connection()
            images = CmdHandler.get_local_image_info(if_print=False)
            for item in images:
                Database.sql_sentence_commit("INSERT INTO images (repository, tag, hash, size) VALUES (%s, %s, %s, %s)", item)
            Database.close_connection()
            print("\033[32mDatabase updated successfully.\033[0m")
        except Exception as e:
            print(f"\033[31mError updating database: {e}\033[0m")

    @staticmethod
    def get_db_image_info():
        try:
            Database.init_connection()
            
            with Database.con.cursor() as cursor:
                cursor.execute("SELECT repository, tag, hash, size FROM images")
                results = cursor.fetchall()   
                
            Database.close_connection()
            print(list(results))
            return list(results)

        except Exception as e:
            print(f"\033[31mError fetching images from database: {e}\033[0m")
            return []

    @staticmethod
    def get_file_image_info(filepath: str):
        try:
            p = Path(filepath)

            if not p.exists():
                print("\033[31mError to find the \"images.json\" file\033[0m")

            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            info_lst = [(item["repo"], item["tag"], item["hash"], item["size"]) for item in data]
            return info_lst
        
        except Exception as e:
            print(f"\033[31mError getting images info: {e}\033[0m")

    @staticmethod
    def pull_images_from_database():
        try:
            Database.init_connection()
            images = CmdHandler.get_db_image_info()

            if platform.system() == "Windows":
                out, err = CmdHandler.__run("docker pull " + " ".join([f"{repo}:{tag}" for repo, tag, _, _ in images]))
            elif platform.system() == "Linux":
                out, err = CmdHandler.__run("sudo docker pull " + " ".join([f"{repo}:{tag}" for repo, tag, _, _ in images]))
            else:
                print(f"\033[31mUnsupported operating system: {platform.system()}\033[0m")
            
            if err:
                print(f"\033[31mError pulling images: {err}\033[0m")

            print(f"\033[34m{out}\033[0m")
        except Exception as e:
            print(f"\033[31mError pulling images: {e}\033[0m")

    @staticmethod
    def export_local_image_file():
        try:
            jsonfile = Path(__file__).parent / "images.json"
            if not jsonfile.exists():
                jsonfile.touch()

            info_lst = CmdHandler.get_local_image_info(if_print=False)
            dict_lst = [{"repo":item[0], "tag":item[1], "hash":item[2], "size":item[3]} for item in info_lst] 
            json_str = json.dumps(dict_lst, indent=2)
            with jsonfile.open("w", encoding="utf-8") as f:
                f.write(json_str)
            print(f"\033[32mImage file exported successfully to path:\033[34m[{jsonfile}]\033[0m")
        except Exception as e:
            print(f"\033[31mError export images file: {e}\033[0m")

    @staticmethod
    def export_local_image_tar(output_dir: str = "./exports"):
        try:
            # ensure export directory exist
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            images = CmdHandler.get_local_image_info()
            if not images:
                print("\033[33mNo images found to export.\033[0m")
                return
            
            for repo, tag, _, _ in images:
                filename = f"{repo}_{tag}.tar"
                output_path = Path(output_dir) / filename
                
                if platform.system() == "Windows":
                    command = f"docker save -o {output_path} {repo}:{tag}"
                elif platform.system() == "Linux":
                    command = f"sudo docker save -o {output_path} {repo}:{tag}"
                else:
                    print(f"\033[31mUnsupported operating system: {platform.system()}\033[0m")
                    return
                    
                out, err = CmdHandler.__run(command)
                
                if err:
                    print(f"\033[31mError exporting {repo}:{tag}: {err}\033[0m")
                else:
                    print(f"\033[32mExported {repo}:{tag} to: {output_path}\033[0m")

                print(f"\033[34m{out}\033[0m")

            print("\033[32mAll images exported successfully.\033[0m")
        except Exception as e:
            print(f"\033[31mError exporting images: {e}\033[0m")


if __name__ == "__main__": 

    pass
import unittest
from unittest.mock import patch, MagicMock
import os
from saveImage import CmdHandler, Database

class TestDatabase(unittest.TestCase):
    
    @patch('saveImage.Connection')
    @patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': '3306', 
        'DB_USER': 'root',
        'DB_PASSWD': 'password',
        'DB_DATABASE': 'test_db'
    })
    def test_init_connection(self, mock_connection):
        # test database connection initialization   
        mock_conn = MagicMock()
        mock_connection.return_value = mock_conn
        
        Database.init_connection()
        
        self.assertTrue(hasattr(Database, 'con'))
        mock_connection.assert_called_once_with(
            host='localhost',
            port=3306,
            user='root', 
            password='password',
            database='test_db'
        )

    def test_sql_sentence_commit_without_connection(self):
        # test SQL execution without connection
        if hasattr(Database, 'con'):
            delattr(Database, 'con')
            
        with self.assertRaises(Exception):
            Database.sql_sentence_commit("SELECT 1")

    @patch('saveImage.Connection')
    def test_sql_sentence_commit_with_params(self, mock_connection):
        # test SQL execution with parameters
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        Database.con = mock_conn
        
        Database.sql_sentence_commit("INSERT INTO test VALUES (%s)", ("value",))
        
        mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES (%s)", ("value",))
        mock_conn.commit.assert_called_once()

    @patch('saveImage.Connection')
    def test_sql_sentence_commit_without_params(self, mock_connection):
        # test SQL execution without parameters
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        Database.con = mock_conn
        
        Database.sql_sentence_commit("SELECT 1")
        
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_conn.commit.assert_called_once()

    def test_close_connection(self):
        # test closing connection
        mock_conn = MagicMock()
        Database.con = mock_conn
        
        Database.close_connection()
        
        mock_conn.close.assert_called_once()
        self.assertFalse(hasattr(Database, 'con'))


class TestCmdHandler(unittest.TestCase):
    
    @patch('saveImage.subprocess.run')
    def test_run_success(self, mock_run):
        # test command execution success
        mock_run.return_value.stdout = "success output"
        mock_run.return_value.stderr = ""
        
        out, err = CmdHandler._CmdHandler__run("test command")
        
        self.assertEqual(out, "success output")
        self.assertEqual(err, "")
        mock_run.assert_called_once_with("test command", shell=True, capture_output=True, text=True)

    @patch('saveImage.subprocess.run')
    def test_run_with_error(self, mock_run):
        # test command execution with error output
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "error message"
        
        out, err = CmdHandler._CmdHandler__run("test command")
        
        self.assertEqual(out, "")
        self.assertEqual(err, "error message")

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_windows(self, mock_run, mock_platform):
        # test getting image information on Windows
        mock_platform.return_value = "Windows"
        mock_run.return_value = ("""REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
alpine       latest    4bcff63911fc   4 weeks ago   12.8MB
debian       12        b6507e340c43   2 weeks ago   181MB""", "")
        
        result = CmdHandler.get_local_image_info()
        
        expected = [('alpine', 'latest', '4bcff63911fc', '12.8MB'),
                   ('debian', '12', 'b6507e340c43', '181MB')]
        self.assertEqual(result, expected)
        mock_run.assert_called_once_with("docker images")

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_linux(self, mock_run, mock_platform):
        # test getting image information on Linux
        mock_platform.return_value = "Linux"
        mock_run.return_value = ("""REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
alpine       latest    4bcff63911fc   4 weeks ago   12.8MB""", "")
        
        result = CmdHandler.get_local_image_info()
        
        expected = [('alpine', 'latest', '4bcff63911fc', '12.8MB')]
        self.assertEqual(result, expected)
        mock_run.assert_called_once_with("sudo docker images")

    @patch('saveImage.platform.system')
    def test_get_local_image_info_unsupported_os(self, mock_platform):
        # test unsupported operating system
        mock_platform.return_value = "MacOS"
        
        result = CmdHandler.get_local_image_info()
        
        self.assertEqual(result, [])

    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_with_error(self, mock_run):
        # test getting image information with error
        mock_run.return_value = ("", "docker: command not found")
        
        result = CmdHandler.get_local_image_info()
        
        self.assertEqual(result, [])

    @patch('saveImage.Database')
    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_update_info_to_db(self, mock_get_images, mock_database):
        # test updating database
        mock_get_images.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        
        CmdHandler.update_info_to_db()
        
        mock_database.init_connection.assert_called_once()
        mock_database.sql_sentence_commit.assert_called_once_with(
            "INSERT INTO images (repository, tag, hash, size) VALUES (%s, %s, %s, %s)",
            ('alpine', 'latest', 'abc123', '12.8MB')
        )
        mock_database.close_connection.assert_called_once()

    @patch('saveImage.Database')
    def test_get_db_image_info(self, mock_database):
        # test getting image information from database
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = (('alpine', 'latest', 'abc123', '12.8MB'),)
        mock_database.con.cursor.return_value.__enter__.return_value = mock_cursor
        
        result = CmdHandler.get_db_image_info()
        
        expected = [('alpine', 'latest', 'abc123', '12.8MB')]
        self.assertEqual(result, expected)
        mock_database.init_connection.assert_called_once()
        mock_database.close_connection.assert_called_once()

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    @patch('saveImage.CmdHandler.get_db_image_info')
    def test_pull_images_from_database_windows(self, mock_get_db, mock_run, mock_platform):
        # test pulling images from database on Windows
        mock_platform.return_value = "Windows"
        mock_get_db.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_run.return_value = ("Successfully pulled", "")
        
        CmdHandler.pull_images_from_database()
        
        mock_run.assert_called_with("docker pull alpine:latest")

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    @patch('saveImage.CmdHandler.get_db_image_info')
    def test_pull_images_from_database_linux(self, mock_get_db, mock_run, mock_platform):
        # test pulling images from database on Linux
        mock_platform.return_value = "Linux"
        mock_get_db.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_run.return_value = ("Successfully pulled", "")
        
        CmdHandler.pull_images_from_database()
        
        mock_run.assert_called_with("sudo docker pull alpine:latest")

    @patch('saveImage.Path')
    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_export_local_image_tar(self, mock_get_images, mock_run, mock_platform, mock_path):
        # test exporting local image to tar
        mock_platform.return_value = "Windows"
        mock_get_images.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_run.return_value = ("", "")
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        
        CmdHandler.export_local_image_tar("./test_exports")
        
        mock_path_instance.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_run.assert_called()

    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_export_local_image_tar_no_images(self, mock_get_images):
        # test exporting when no images are available
        mock_get_images.return_value = []
        
        CmdHandler.export_local_image_tar()
        
        # should not raise an exception, just print a warning


if __name__ == '__main__':
    ### Test written by Claude Sonnet 4 ###
    unittest.main()

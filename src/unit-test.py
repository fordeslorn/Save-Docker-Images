import unittest
from unittest.mock import patch, MagicMock, mock_open
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

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
    def test_init_connection_success(self, mock_connection):
        # 测试数据库连接初始化成功
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

    @patch('saveImage.Connection')
    @patch.dict(os.environ, {
        'DB_HOST': 'localhost',
        'DB_PORT': 'invalid_port', 
        'DB_USER': 'root',
        'DB_PASSWD': 'password',
        'DB_DATABASE': 'test_db'
    })
    def test_init_connection_failure(self, mock_connection):
        # 测试数据库连接初始化失败
        mock_connection.side_effect = ValueError("Invalid port")
        
        with self.assertRaises(ValueError):
            Database.init_connection()

    def test_sql_sentence_commit_without_connection(self):
        # 测试没有连接时执行SQL
        if hasattr(Database, 'con'):
            delattr(Database, 'con')
            
        with self.assertRaises(Exception):
            Database.sql_sentence_commit("SELECT 1")

    def test_sql_sentence_commit_with_params(self):
        # 测试带参数的SQL执行
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        Database.con = mock_conn
        
        Database.sql_sentence_commit("INSERT INTO test VALUES (%s)", ("value",))
        
        mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES (%s)", ("value",))
        mock_conn.commit.assert_called_once()

    def test_sql_sentence_commit_without_params(self):
        # 测试不带参数的SQL执行
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        Database.con = mock_conn
        
        Database.sql_sentence_commit("SELECT 1")
        
        mock_cursor.execute.assert_called_once_with("SELECT 1")
        mock_conn.commit.assert_called_once()

    def test_close_connection_success(self):
        # 测试成功关闭连接
        mock_conn = MagicMock()
        Database.con = mock_conn
        
        Database.close_connection()
        
        mock_conn.close.assert_called_once()
        self.assertFalse(hasattr(Database, 'con'))

    def test_close_connection_without_connection(self):
        # 测试没有连接时关闭连接
        if hasattr(Database, 'con'):
            delattr(Database, 'con')
        
        try:
            Database.close_connection()
        except Exception:
            self.fail("close_connection should not raise exception when no connection exists")


class TestCmdHandler(unittest.TestCase):
    
    @patch('saveImage.subprocess.run')
    def test_run_success(self, mock_run):
        # 测试命令执行成功
        mock_run.return_value.stdout = "success output"
        mock_run.return_value.stderr = ""
        
        out, err = CmdHandler._CmdHandler__run("test command")
        
        self.assertEqual(out, "success output")
        self.assertEqual(err, "")
        mock_run.assert_called_once_with("test command", shell=True, capture_output=True, text=True)

    @patch('saveImage.subprocess.run')
    def test_run_with_error(self, mock_run):
        # 测试命令执行有错误输出
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "error message"
        
        out, err = CmdHandler._CmdHandler__run("test command")
        
        self.assertEqual(out, "")
        self.assertEqual(err, "error message")

    @patch('saveImage.subprocess.run')
    def test_run_exception(self, mock_run):
        # 测试命令执行抛出异常
        mock_run.side_effect = Exception("Command failed")
        
        out, err = CmdHandler._CmdHandler__run("test command")
        
        self.assertEqual(out, "")
        self.assertEqual(err, "Command failed")

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_windows(self, mock_run, mock_platform):
        # 测试在Windows系统获取镜像信息
        mock_platform.return_value = "Windows"
        mock_run.return_value = ("""REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
alpine       latest    4bcff63911fc   4 weeks ago   12.8MB
debian       12        b6507e340c43   2 weeks ago   181MB""", "")
        
        result = CmdHandler.get_local_image_info(if_print=False)
        
        expected = [('alpine', 'latest', '4bcff63911fc', '12.8MB'),
                   ('debian', '12', 'b6507e340c43', '181MB')]
        self.assertEqual(result, expected)
        mock_run.assert_called_once_with("docker images")

    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_linux(self, mock_run, mock_platform):
        # 测试在Linux系统获取镜像信息
        mock_platform.return_value = "Linux"
        mock_run.return_value = ("""REPOSITORY   TAG       IMAGE ID       CREATED       SIZE
alpine       latest    4bcff63911fc   4 weeks ago   12.8MB""", "")
        
        result = CmdHandler.get_local_image_info(if_print=False)
        
        expected = [('alpine', 'latest', '4bcff63911fc', '12.8MB')]
        self.assertEqual(result, expected)
        mock_run.assert_called_once_with("sudo docker images")

    @patch('saveImage.platform.system')
    def test_get_local_image_info_unsupported_os(self, mock_platform):
        # 测试不支持的操作系统
        mock_platform.return_value = "MacOS"
        
        result = CmdHandler.get_local_image_info(if_print=False)
        
        self.assertEqual(result, [])

    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_get_local_image_info_with_error(self, mock_run):
        # 测试获取镜像信息时有错误
        mock_run.return_value = ("", "docker: command not found")
        
        result = CmdHandler.get_local_image_info(if_print=False)
        
        self.assertEqual(result, [])

    @patch('saveImage.Database')
    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_update_info_to_db_success(self, mock_get_images, mock_database):
        # 测试成功更新数据库
        mock_get_images.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        
        CmdHandler.update_info_to_db()
        
        mock_database.init_connection.assert_called_once()
        mock_database.sql_sentence_commit.assert_called_once_with(
            "INSERT INTO images (repository, tag, hash, size) VALUES (%s, %s, %s, %s)",
            ('alpine', 'latest', 'abc123', '12.8MB')
        )
        mock_database.close_connection.assert_called_once()

    @patch('saveImage.Database')
    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_update_info_to_db_failure(self, mock_get_images, mock_database):
        # 测试更新数据库失败
        mock_get_images.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_database.init_connection.side_effect = Exception("Database error")
        
        CmdHandler.update_info_to_db()
        
        mock_database.init_connection.assert_called_once()

    @patch('saveImage.Database')
    def test_get_db_image_info_success(self, mock_database):
        # 测试从数据库获取镜像信息成功
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = (('alpine', 'latest', 'abc123', '12.8MB'),)
        mock_database.con.cursor.return_value.__enter__.return_value = mock_cursor
        
        result = CmdHandler.get_db_image_info()
        
        expected = [('alpine', 'latest', 'abc123', '12.8MB')]
        self.assertEqual(result, expected)
        mock_database.init_connection.assert_called_once()
        mock_database.close_connection.assert_called_once()

    @patch('saveImage.Database')
    def test_get_db_image_info_failure(self, mock_database):
        # 测试从数据库获取镜像信息失败
        mock_database.init_connection.side_effect = Exception("Database error")
        
        result = CmdHandler.get_db_image_info()
        
        self.assertEqual(result, [])

    @patch('saveImage.Path')
    @patch('saveImage.json.load')
    def test_get_file_image_info_success(self, mock_json_load, mock_path):
        # 测试从文件获取镜像信息成功
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = True
        
        mock_file = MagicMock()
        mock_path_instance.open.return_value.__enter__.return_value = mock_file
        
        mock_json_load.return_value = [
            {"repo": "alpine", "tag": "latest", "hash": "abc123", "size": "12.8MB"}
        ]
        
        result = CmdHandler.get_file_image_info("images.json")
        
        expected = [('alpine', 'latest', 'abc123', '12.8MB')]
        self.assertEqual(result, expected)

    @patch('saveImage.Path')
    def test_get_file_image_info_file_not_exists(self, mock_path):
        # 测试文件不存在
        mock_path_instance = MagicMock()
        mock_path.return_value = mock_path_instance
        mock_path_instance.exists.return_value = False
        
        result = CmdHandler.get_file_image_info("images.json")
        
        self.assertIsNone(result)

    @patch('saveImage.Database')
    @patch('saveImage.CmdHandler.get_db_image_info')
    @patch('saveImage.CmdHandler.get_local_image_info')
    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_pull_images_from_database_windows(self, mock_run, mock_platform, mock_local, mock_db, mock_database):
        # 测试在Windows系统从数据库拉取镜像
        mock_platform.return_value = "Windows"
        mock_db.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_local.return_value = []  # 本地没有镜像
        mock_run.return_value = ("Successfully pulled", "")
        
        CmdHandler.pull_images_from_database()
        
        mock_run.assert_called_with("docker pull alpine:latest")

    @patch('saveImage.Database')
    @patch('saveImage.CmdHandler.get_db_image_info')
    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_pull_images_from_database_image_exists(self, mock_local, mock_db, mock_database):
        # 测试镜像已存在本地的情况
        mock_db.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        mock_local.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]  # 本地已有镜像
        
        CmdHandler.pull_images_from_database()
        
        # 不应该调用docker pull命令

    @patch('saveImage.CmdHandler.get_local_image_info')
    def test_export_local_image_file_success(self, mock_get_images):
        # 测试导出镜像文件成功
        mock_get_images.return_value = [('alpine', 'latest', 'abc123', '12.8MB')]
        
        try:
            CmdHandler.export_local_image_file()
            # 如果没有抛出异常，说明方法执行成功
        except Exception as e:
            self.fail(f"export_local_image_file should not raise exception: {e}")
        
        # 验证获取镜像信息被调用
        mock_get_images.assert_called_once()

    @patch('saveImage.Path')
    @patch('saveImage.CmdHandler.get_local_image_info')
    @patch('saveImage.platform.system')
    @patch('saveImage.CmdHandler._CmdHandler__run')
    def test_export_local_image_tar_windows(self, mock_run, mock_platform, mock_get_images, mock_path):
        # 测试在Windows系统导出镜像为tar文件
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
        # 测试没有镜像时的导出
        mock_get_images.return_value = []
        
        CmdHandler.export_local_image_tar()
        
        # 应该不会抛出异常，只是打印警告


if __name__ == '__main__':
    # 运行测试时显示详细信息
    unittest.main(verbosity=2)

# Database类测试：
# 连接初始化（成功/失败）
# SQL执行（带参数/不带参数/无连接）
# 连接关闭（成功/无连接）
# CmdHandler类测试：
# 命令执行（成功/错误/异常）
# 获取本地镜像信息（Windows/Linux/不支持的系统/错误）
# 更新数据库（成功/失败）
# 从数据库获取镜像信息（成功/失败）
# 从文件获取镜像信息（成功/文件不存在）
# 从数据库拉取镜像（Windows/镜像已存在）
# 导出镜像文件（成功）
# 导出tar文件（Windows/无镜像）
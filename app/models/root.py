from aiomysql.connection import Connection
from aiomysql.cursors import Cursor

from app.db import MysqlConnection
from app.log import ExceptionLogger
from app.response import JSONResponse, ResponseDict



class RootModel:
    '''数据库管理相关的操作'''
    @ExceptionLogger.handle_database_exception_async
    async def get_innodb_trx() -> ResponseDict:
        '''检测数据库是否有未提交的事务'''
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = []
            await cur.execute(
                "SELECT trx_id, trx_mysql_thread_id, trx_started, trx_state, trx_query "
                "FROM INFORMATION_SCHEMA.INNODB_TRX "
                "WHERE trx_state = 'RUNNING';"
            )
            rows = await cur.fetchall()
            for row in rows:
                data.append({
                    'id': row[0],
                    'thread_id': row[1],
                    'strated': row[2],
                    'state': row[3],
                    'query': row[4]
                })
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)

    @ExceptionLogger.handle_database_exception_async
    async def kill_trx(thread_id: str) -> ResponseDict:
        '''删除未提交事务的thread_id'''
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            await cur.execute(
                "KILL %s;"
                [thread_id]
            )
            await conn.commit()
            return JSONResponse.API_1000_Success
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)

    @ExceptionLogger.handle_database_exception_async
    async def get_innodb_processlist() -> ResponseDict:
        '''获取数据库的连接数'''
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = []
            await cur.execute(
                "SHOW PROCESSLIST;"
            )
            rows = await cur.fetchall()
            for row in rows:
                data.append({
                    'id': row[0],
                    'user': row[1],
                    'host': row[2],
                    'db': row[3],
                    'command': row[4],
                    'time': row[5],
                    'state': row[6],
                    'info': row[7]
                })
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)

    
    @ExceptionLogger.handle_database_exception_async
    async def get_basic_user_overview():
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = {}
            await cur.execute(
                "SELECT r.region_str, COALESCE(COUNT(u.region_id), 0) AS count "
                "FROM region AS r "
                "LEFT JOIN user_basic AS u ON r.region_id = u.region_id "
                "WHERE r.region_id BETWEEN 1 AND 5 "
                "GROUP BY r.region_id, r.region_str;"
            )
            users = await cur.fetchall()
            for user in users:
                data[user[0]] = user[1]
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)

    
    @ExceptionLogger.handle_database_exception_async
    async def get_basic_clan_overview():
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = {}
            await cur.execute(
                "SELECT r.region_str, COALESCE(COUNT(u.region_id), 0) AS count "
                "FROM region AS r "
                "LEFT JOIN user_basic AS u ON r.region_id = u.region_id "
                "WHERE r.region_id BETWEEN 1 AND 5 "
                "GROUP BY r.region_id, r.region_str;"
            )
            users = await cur.fetchall()
            for user in users:
                data[user[0]] = user[1]
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)

    
    @ExceptionLogger.handle_database_exception_async
    async def get_recent_user_overview():
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = {}
            await cur.execute(
                "SELECT r.region_str, COALESCE(COUNT(u.region_id), 0) AS count "
                "FROM region AS r "
                "LEFT JOIN recent AS u ON r.region_id = u.region_id "
                "WHERE r.region_id BETWEEN 1 AND 5 "
                "GROUP BY r.region_id, r.region_str;"
            )
            users = await cur.fetchall()
            for user in users:
                data[user[0]] = user[1]
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)


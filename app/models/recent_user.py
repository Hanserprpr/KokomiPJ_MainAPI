from aiomysql.connection import Connection
from aiomysql.cursors import Cursor

from app.db import MysqlConnection
from app.log import ExceptionLogger
from app.response import JSONResponse, ResponseDict
from app.utils import TimeFormat


class RecentUserModel:
    @ExceptionLogger.handle_database_exception_async
    async def get_recent_user_by_rid(region_id: int) -> ResponseDict:
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            data = []
            await cur.execute(
                "SELECT account_id FROM recent WHERE region_id = %s;",
                [region_id]
            )
            users = await cur.fetchall()
            for user in users:
                data.append(user[0])
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
    async def check_recent_user(account_id: int, region_id: int) -> ResponseDict:
        try:
            conn: Connection = await MysqlConnection.get_connection()
            cur: Cursor = await conn.cursor()
            data = {
                'enabled': False
            }
            await cur.execute(
                "SELECT EXISTS(SELECT 1 FROM recent WHERE region_id = %s and account_id = %s) AS is_exists_user;",
                [region_id, account_id]
            )
            user = await cur.fetchone()
            if user[0]:
                data['enabled'] = True
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
    async def add_recent_user(account_id: int, region_id: int, recent_class: int) -> ResponseDict:
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            await cur.execute(
                "SELECT recent_class FROM recent WHERE region_id = %s and account_id = %s;", 
                [region_id, account_id]
            )
            user = await cur.fetchone()
            if user is None:
                # 用户不存在，插入新用户
                current_timestamp = TimeFormat.get_current_timestamp()
                await cur.execute(
                    "INSERT INTO recent (account_id, region_id, recent_class, last_query_time) VALUES (%s, %s, %s, %s);",
                    [account_id, region_id, recent_class, current_timestamp]
                )
                await conn.commit()
            else:
                if user[0] <= recent_class:
                    await cur.execute(
                        "UPDATE recent SET recent_class = %s WHERE region_id = %s and account_id = %s;",
                        [recent_class, region_id, account_id]
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
    async def del_recent_user(account_id: int, region_id: int) -> ResponseDict:
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            await cur.execute(
                "DELETE FROM recent WHERE region_id = %s and account_id = %s;",
                [region_id, account_id]
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
    async def update_recent_user(user_recent: dict) -> ResponseDict:
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            account_id = user_recent['account_id']
            region_id = user_recent['region_id']
            await cur.execute(
                "SELECT recent_class, last_query_time, last_update_time "
                "FROM recent WHERE region_id = %s and account_id = %s;", 
                [region_id, account_id]
            )
            user = await cur.fetchone()
            if user == None:
                return JSONResponse.API_1020_UserNotFoundInDatabase
            sql_str = ''
            params = []
            i = 0
            for user_recent_key in ['recent_class', 'last_query_time', 'last_update_time']:
                if user_recent.get(user_recent_key) == None:
                    i += 1
                    continue
                if user[i] != user_recent.get(user_recent_key):
                    sql_str += f'{user_recent_key} = %s, '
                    params.append(user_recent.get(user_recent_key))
                i += 1
            params = params + [region_id, account_id]
            await cur.execute(
                f"UPDATE recent SET {sql_str}updated_at = CURRENT_TIMESTAMP WHERE region_id = %s and account_id = %s;",
                params
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
    async def get_user_recent_data(account_id: int, region_id: int) -> ResponseDict:
        '''获取用户recent表的数据'''
        conn: Connection = await MysqlConnection.get_connection()
        cur: Cursor = await conn.cursor()
        try:
            await cur.execute(
                "SELECT u.is_active, u.active_level, u.is_public, u.total_battles, u.last_battle_time, UNIX_TIMESTAMP(u.updated_at) AS update_time, "
                "r.recent_class, r.last_query_time, r.last_update_time "
                "FROM recent AS r "
                "LEFT JOIN user_info AS u ON u.account_id = r.account_id "
                "WHERE r.region_id = %s and r.account_id = %s;",
                [region_id, account_id]
            )
            user = await cur.fetchone()
            if user:
                data = {
                    'user_recent': {
                        'recent_class': user[6],
                        'last_query_time': user[7],
                        'last_update_time': user[8]
                    },
                    'user_info': {
                        'is_active': user[0],
                        'active_level': user[1],
                        'is_public': user[2],
                        'total_battles': user[3],
                        'last_battle_time': user[4],
                        'update_time': user[5]
                    }
                }
            else:
                return JSONResponse.API_1020_UserNotFoundInDatabase
            return JSONResponse.get_success_response(data)
        except Exception as e:
            # 数据库回滚
            await conn.rollback()
            raise e
        finally:
            # 释放资源
            await cur.close()
            await MysqlConnection.release_connection(conn)
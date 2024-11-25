from typing import Optional

from app.models import UserModel, ClanModel
from app.utils import UtilityFunctions
from app.network import BasicAPI
from app.response import JSONResponse, ResponseDict
from app.middlewares.celery import (
    task_check_user_basic, 
    task_check_clan_basic, 
    task_update_user_clan, 
    task_check_user_info,
    task_update_clan_and_user
)

async def get_user_name_and_clan(
    account_id: int,
    region_id: str,
    ac_value: Optional[str] = None
) -> ResponseDict:
    '''获取用户的基本数据(name+clan)

    这是一个公用函数，用于获取用户名称、工会以及状态

    参数：
        account_id: 用户id
        region_id: 服务器id
        ac_value: ac值

    返回：
        JSONResponse
    '''

    '''
    请求处理逻辑/
    ├── 1. 从数据库中读取数据(user_basic,user_clan,clan_basic)
    ├── 2. 首次请求接口获取用户和工会的基础数据/
    │   └── (后台任务) 更新user_basic,user_clan和clan_basic表
    ├── 3. 从用户基础数据，判断用户的状态(is_acctive,is_public等)/
    │   └── (后台任务) 更新user_info表
    └── 4. 返回结果
    '''
    # 返回的user和clan数据格式
    user_basic = {
        'id': account_id,
        'name': UtilityFunctions.get_user_default_name(account_id),
        'karma': 0,
        'crated_at': 0,
        'actived_at': 0,
        'dog_tag': {}
    }
    clan_basic = {
        'id': None,
        'tag': None,
        'league': None
    }
    # 用于后台更新user_info表的数据
    user_info = {
        'account_id': account_id,
        'region_id': region_id,
        'is_active': True,
        'active_level': 0,
        'is_public': True,
        'total_battles': 0,
        'last_battle_time': 0
    }
    # 获取用户的username
    user_basic_result: dict = await UserModel.get_user_name_by_id(account_id, region_id)
    if user_basic_result.get('code',None) != 1000:
        return user_basic_result
    user_basic['name'] = user_basic_result['data']['nickname']

    # 获取用户所在工会的clan_id
    user_clan_result: dict = await UserModel.get_user_clan_id(account_id,region_id)
    if user_clan_result.get('code',None) != 1000:
        return user_clan_result
    valid_clan = True
    # 判断用户所在工会数据是否有效
    if not UtilityFunctions.check_clan_vaild(user_clan_result['data']['updated_at']):
        valid_clan = False
    # 工会的tag和league
    if valid_clan and user_clan_result['data']['clan_id']:
        # 如果有效则获取工会tag和league
        clan_basic_result = await ClanModel.get_clan_tag_and_league(
            user_clan_result['data']['clan_id'],
            region_id
        )
        # 判断工会数据是否有效
        if not UtilityFunctions.check_clan_vaild(clan_basic_result['data']['updated_at']):
            valid_clan = False
        else:
            clan_basic['id'] = user_clan_result['data']['clan_id']
            clan_basic['tag'] = clan_basic_result['data']['tag']
            clan_basic['league'] = clan_basic_result['data']['league']
    
    # 如果clan数据有效则只请求user数据，否则请求user和clan数据
    if valid_clan:
        basic_data = await BasicAPI.get_user_basic(account_id,region_id,ac_value)
    else:
        basic_data = await BasicAPI.get_user_basic_and_clan(account_id,region_id,ac_value)

    for response in basic_data:
        if response['code'] != 1000 and response['code'] != 1001:
            return response
    # 用户数据
    if basic_data[0]['code'] == 1001:
        # 用户数据不存在
        user_info['is_active'] = False
        if not valid_clan:
            #处理工会信息
            user_clan_data = basic_data[1]['data']
            if user_clan_data['clan_id'] != None:
                clan_basic['id'] = user_clan_data['clan_id']
                clan_basic['tag'] = user_clan_data['clan']['tag']
                clan_basic['league'] = UtilityFunctions.get_league_by_color(user_clan_data['clan']['color'])
                task_update_clan_and_user(
                    {
                    'clan_id': clan_basic['id'],
                    'region_id': region_id,
                    'tag': clan_basic['tag'],
                    'league': clan_basic['league']
                    },
                    {
                        'account_id': user_basic['id'],
                        'clan_id': clan_basic['id']
                    }
                )
            else:
                task_update_user_clan.delay({
                    'account_id': user_basic['id'],
                    'clan_id': None
                })
        task_check_user_info.delay(user_info)
        return JSONResponse.API_1001_UserNotExist
    if user_basic_result['data']['nickname'] != basic_data[0]['data'][str(account_id)]['name']:
        # 用户名称改变
        user_basic['name'] = basic_data[0]['data'][str(account_id)]['name']
        task_check_user_basic.delay({
            'account_id':account_id,
            'region_id':region_id,
            'nickname':user_basic['name']
        })
    if 'hidden_profile' in basic_data[0]['data'][str(account_id)]:
        # 隐藏战绩
        user_info['is_public'] = False
        user_info['active_level'] = UtilityFunctions.get_active_level(user_info)
        if not valid_clan:
            #处理工会信息
            user_clan_data = basic_data[1]['data']
            if user_clan_data['clan_id'] != None:
                clan_basic['id'] = user_clan_data['clan_id']
                clan_basic['tag'] = user_clan_data['clan']['tag']
                clan_basic['league'] = UtilityFunctions.get_league_by_color(user_clan_data['clan']['color'])
                task_update_clan_and_user(
                    {
                    'clan_id': clan_basic['id'],
                    'region_id': region_id,
                    'tag': clan_basic['tag'],
                    'league': clan_basic['league']
                    },
                    {
                        'account_id': user_basic['id'],
                        'clan_id': clan_basic['id']
                    }
                )
            else:
                task_update_user_clan.delay({
                    'account_id': user_basic['id'],
                    'clan_id': None
                })
        task_check_user_info.delay(user_info)
        if ac_value:
            return JSONResponse.API_1013_ACisInvalid
        else:
            return JSONResponse.API_1005_UserHiddenProfite
    user_basic_data = basic_data[0]['data'][str(account_id)]['statistics']
    if (
        user_basic_data == {} or
        user_basic_data['basic'] == {}
    ):
        # 用户没有数据
        user_info['is_active'] = False
        task_check_user_info.delay(user_info)
        return JSONResponse.API_1006_UserDataisNone
    if user_basic_data['basic']['leveling_points'] == 0:
        # 用户没有数据
        user_info['total_battles'] = 0
        user_info['last_battle_time'] = 0
        user_info['active_level'] = 1
        task_check_user_info.delay(user_info)
        return JSONResponse.API_1006_UserDataisNone
    # 获取user_info的数据并更新数据库
    user_info['total_battles'] = user_basic_data['basic']['leveling_points']
    user_info['last_battle_time'] = user_basic_data['basic']['last_battle_time']
    user_info['active_level'] = UtilityFunctions.get_active_level(user_info)
    task_check_user_info.delay(user_info)
    # 获取user_basic的数据
    user_basic['karma'] = user_basic_data['basic']['karma']
    user_basic['crated_at'] = user_basic_data['basic']['created_at']
    user_basic['actived_at'] = user_basic_data['basic']['last_battle_time']
    user_basic['dog_tag'] = basic_data[0]['data'][str(account_id)]['dog_tag']
    if not valid_clan:
        #处理工会信息
        user_clan_data = basic_data[1]['data']
        if user_clan_data['clan_id'] != None:
            clan_basic['id'] = user_clan_data['clan_id']
            clan_basic['tag'] = user_clan_data['clan']['tag']
            clan_basic['league'] = UtilityFunctions.get_league_by_color(user_clan_data['clan']['color'])
            task_check_clan_basic.delay({
                'clan_id': clan_basic['id'],
                'region_id': region_id,
                'tag': clan_basic['tag'],
                'league': clan_basic['league']
            })
            task_update_user_clan.delay({
                'account_id': user_basic['id'],
                'clan_id': clan_basic['id']
            })
        else:
            task_update_user_clan.delay({
                'account_id': user_basic['id'],
                'clan_id': None
            })
    # 返回user和clan数据
    data = {
        'user': user_basic,
        'clan': clan_basic
    }
    return JSONResponse.get_success_response(data)

import requests
import json
from datetime import datetime,timedelta
from typing import List, Dict
import aiohttp
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
class ChinaRailway:
    station_code: Dict[str, str] = {}
    station_name: Dict[str, str] = {}

    @staticmethod
    async def get_station_data():
        if not ChinaRailway.station_code:
            try:
                connector = aiohttp.TCPConnector(ssl=False)  # 创建不验证 SSL 的连接器
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get('https://kyfw.12306.cn/otn/resources/js/framework/station_name.js') as response:
                        text = await response.text()
                        station_list_str = text.split("='")[1].split("';")[0]  # 简化匹配逻辑
                        station_list = station_list_str.split('@')[1:]  # 跳过第一个空元素
                        for station in station_list:
                            details = station.split('|')
                            if len(details) >= 3:
                                ChinaRailway.station_code[details[1]] = details[2]  # 城市代码到名称
                                ChinaRailway.station_name[details[2]] = details[1]  # 名称到代码
            except Exception as e:
                raise Exception(f"获取站数据失败: {str(e)}")

    @staticmethod
    async def get_station_code(name: str):
        if not ChinaRailway.station_code:
            await ChinaRailway.get_station_data()
        return ChinaRailway.station_code.get(name)

    @staticmethod
    async def find_cities(city_name: str):
        if not ChinaRailway.station_code:
            await ChinaRailway.get_station_data()
        match_cities = []
        for station_key in ChinaRailway.station_code:
            if station_key == city_name:
                return [ChinaRailway.station_code[station_key]]  # 完全匹配
            elif city_name in station_key:
                match_cities.append(ChinaRailway.station_code[station_key])
        return match_cities

    @staticmethod
    async def search_tickets(date_str: str, from_city: str, to_city: str):
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            now = datetime.now()
            if now >= date_obj or (now + timedelta(days=15)) < date_obj:
                raise Exception('日期需为0~15天内')

            from_cities = await ChinaRailway.find_cities(from_city)
            if not from_cities:
                raise Exception(f'没有找到出发城市: {from_city}')

            to_cities = await ChinaRailway.find_cities(to_city)
            if not to_cities:
                raise Exception(f'没有找到到达城市: {to_city}')

            from_city_code = from_cities[0]
            to_city_code = to_cities[0]

            # 获取 Cookie（简化处理，实际可能需要更复杂的会话管理）
            session = requests.Session()
            session.get('https://kyfw.12306.cn/')
            cookies = '; '.join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])

            api_url = (
                f'https://kyfw.12306.cn/otn/leftTicket/queryG?'
                f'leftTicketDTO.train_date={date_obj.strftime("%Y-%m-%d")}'
                f'&leftTicketDTO.from_station={from_city_code}'
                f'&leftTicketDTO.to_station={to_city_code}'
                f'&purpose_codes=ADULT'
            )

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
                'Cookie': cookies
            }

            response = session.get(api_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data or not data.get('status'):
                raise Exception('获取余票数据失败')

            result = data.get('data', {}).get('result', [])
            map_data = data.get('data', {}).get('map', {})
            parsed_list = ChinaRailway.parse_train_info(result, map_data)
            return parsed_list

        except Exception as e:
            e
            raise Exception(str(e))

    @staticmethod
    def _parse_price_number(da):
        if da == "0":
            return ""
        return f"{float(da)/10:.1f}"  # 简化价格解析

    @staticmethod
    def _parse_price(df):
        dh = ""
        c9 = {}
        dd = len(df) // 7
        for dc in range(dd):
            dg = df[dc * 7:(dc * 7) + 7]
            db = dg[0]
            de = dg[1]
            da = ChinaRailway._parse_price_number(dg[2:])
            dh += db
            c9[db + de] = da
        c9['all'] = dh
        return c9

    @staticmethod
    def _parse_price2(de):
        df = {}
        dd = len(de) // 10
        for da in range(dd):
            dc = de[da * 10:(da * 10) + 10]
            c9 = dc[0]
            db = dc[6]
            dg = ChinaRailway._parse_price_number(dc[1:6])
            if db == "3":
                df['W'] = dg
            else:
                df[c9] = dg
        return df

    @staticmethod
    def parse_train_info(strs: List[str], map_data: Dict[str, str]) -> List[Dict]:
        list_data = []
        for str_item in strs:
            arr = str_item.split('|')
            data = {
                'secretStr': arr[0],
                'buttonTextInfo': arr[1],
                'train_no': arr[2],
                'station_train_code': arr[3],
                'start_station_telecode': arr[4],
                'end_station_telecode': arr[5],
                'from_station_telecode': arr[6],
                'to_station_telecode': arr[7],
                'start_time': arr[8],
                'arrive_time': arr[9],
                'lishi': arr[10],
                'canWebBuy': arr[11],
                'yp_info': arr[12],
                'start_train_date': arr[13],
                'train_seat_feature': arr[14],
                'location_code': arr[15],
                'from_station_no': arr[16],
                'to_station_no': arr[17],
                'is_support_card': arr[18],
                'controlled_train_flag': arr[19],
                'gg_num': arr[20],
                'gr_num': arr[21],
                'qt_num': arr[22],
                'rw_num': arr[23],
                'rz_num': arr[24],
                'tz_num': arr[25],
                'wz_num': arr[26],
                'yb_num': arr[27],
                'yw_num': arr[28],
                'yz_num': arr[29],
                'ze_num': arr[30],
                'zy_num': arr[31],
                'swz_num': arr[32],
                'srrb_num': arr[33],
                'yp_ex': arr[34],
                'seat_types': arr[35],
                'exchange_train_flag': arr[36],
                'houbu_train_flag': arr[37],
                'houbu_seat_limit': arr[38],
                'yp_info_new': arr[39],
                'dw_flag': arr[46],
                'stopcheckTime': arr[48],
                'country_flag': arr[49],
                'local_arrive_time': arr[50],
                'local_start_time': arr[51],
                'bed_level_info': arr[53],
                'seat_discount_info': arr[54],
                'sale_time': arr[55],
                'from_station_name': map_data.get(arr[6]),
                'to_station_name': map_data.get(arr[7]),
            }
            ticket_prices = ChinaRailway._parse_price2(data['yp_info_new'])
            data['tickets'] = {
                '商务座': {'num': data['swz_num'] or '-', 'price': ticket_prices.get('9') or ticket_prices.get('P') or '-'},
                '特等座': {'num': data['tz_num'] or '-', 'price': ticket_prices.get('9') or ticket_prices.get('P') or '-'},
                '优选一等座': {'num': data['gg_num'] or '-', 'price': ticket_prices.get('D') or '-'},
                '一等座': {'num': data['zy_num'] or '-', 'price': ticket_prices.get('M') or '-'},
                '二等座': {'num': data['ze_num'] or '-', 'price': ticket_prices.get('O') or ticket_prices.get('S') or '-'},
                '高级软卧': {'num': data['gr_num'] or '-', 'price': ticket_prices.get('6') or '-'},
                '软卧': {'num': data['rw_num'] or '-', 'price': ticket_prices.get('4') or ticket_prices.get('I') or ticket_prices.get('F') or '-'},
                '硬卧': {'num': data['yw_num'] or '-', 'price': ticket_prices.get('3') or ticket_prices.get('J') or '-'},
                '软座': {'num': data['rz_num'] or '-', 'price': ticket_prices.get('2') or '-'},
                '硬座': {'num': data['yz_num'] or '-', 'price': ticket_prices.get('1') or '-'},
                '无座': {'num': data['wz_num'] or '-', 'price': ticket_prices.get('W') or '-'},
                '其他': {'num': data['qt_num'] or '-', 'price': ticket_prices.get('D') or ticket_prices.get('E') or ticket_prices.get('G') or ticket_prices.get('H') or ticket_prices.get('Q') or '-'},
            }
            list_data.append(data)
        return list_data

app = FastAPI(title="火车票次查询", version="1.0.0")
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def search_endpoint(date: str, from_city: str, to_city: str):
    try:
        tickets = await ChinaRailway.search_tickets(date, from_city, to_city)
        result_list = []
        for item in tickets:
            result_list.append({
                "车次": item['station_train_code'],
                "出发站": item['from_station_name'],
                "到达站": item['to_station_name'],
                "出发时间": item['start_time'],
                "到达时间": item['arrive_time'],
                "历时": item['lishi'],
                "备注": item['buttonTextInfo'],
                "票列表": item['tickets']
            })
        return {"content": result_list}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/search",
        summary="查询火车票",
        description="使用日期、出发城市和到达城市查询火车票信息。参数：date (YYYY-MM-DD)，from_city (出发城市)，to_city (到达城市)")
async def search(date: str, from_city: str, to_city: str):
    print("123")
    return await search_endpoint(date, from_city, to_city)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=3000)

# create_script
create_script

1. 5-13 초기 세팅
    git
    conda
    requirements.txt
    Python 3.11.11


    # 천개 이미지 유알엘만 크롤링하고 제미나이 코멘트를 디비에 넣기
# arun_many 버전
import asyncio
from crawl4ai import *
import duckdb 
import pandas as pd
from pathlib import Path
import requests
from google import genai
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import time

hz_urls = "https://www.houzz.com/photos/kitchen-ideas-and-designs-phbr0-bp~t_709"
#headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) like Gecko'}
db_name = "hz_data6.duckdb"
#image_path = './hz_images3'
from_index = 35
crawl_count = 1000

hzdb = duckdb.connect(db_name)
load_dotenv(dotenv_path='/home/admusr/cis/.env')

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

# 주방 바닥재,캐비넷,상판 정보. 제미나이 출력 정보
class Kitchen(BaseModel):
    flooring_color: str
    flooring_color_rgb:str
    flooring_material:str
    flooring_pattern: str
    flooring_design_special_feature:str
    flooring_designer_comment:str
    cabinet_color: str
    cabinet_color_rgb:str
    cabinet_material:str
    cabinet_pattern: str
    cabinet_design_special_feature:str
    cabinet_designer_comment:str
    countertop_color: str
    countertop_color_rgb:str
    countertop_material:str
    countertop_pattern: str
    countertop_design_special_feature:str
    countertop_designer_comment:str


# 제미나이 콜하고 딕셔너리 받는다.
async def process_kitchen_image_by_gemini(client, url, page_number):
    print(f"====== llm process : {page_number}")
    image = requests.get(url,headers)
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=[image,"""현재 주방 이미지에서 바닥재,캐비넷,상판 각각에 대해서 색깔,대표 색깔의 RGB값, 무늬, 디자인의 특징, 전문 디자이너의 논평내용들을 각각 말해줘. \n
            잘 안보이는 것은 '없음'이라고 표기해줘."""],
        config={
            'system_instruction':"너는 주방 전문 디자이너야. 특히 바닥재(flooring),캐비넷(cabinet),상판(countertop)에 대한 전문가야. 항상 한국말로 답변해 줘.",
            'response_mime_type': 'application/json',
            'response_schema': Kitchen,
            'temperature': 0.1,
        },
    )
    await asyncio.sleep(5) #time.sleep(5) # gemini free 15/minute limit
    my_kitchen: Kitchen = response.parsed
    k_dict = my_kitchen.model_dump()
    k_dict['page'] = page_number
    k_dict['image_url'] = url
    print(k_dict)
    return k_dict
    

# return url list from staring page to end page 
def get_url_list(hz_url,f,cnt):
    return [hz_url+'?pg='+str(i+f) for i in range(int(cnt/20))]

# 안씀.임시테이블 넣고 테이블 후처리
def create_tables(conn):
    conn.sql("""
    create table if not exists hz_links_temp(
        plink varchar,
        ptext varchar,
        page integer
    )""")
    conn.sql("""
    create table if not exists hz_img_temp(
        psrc varchar,
        pdesc varchar,
        page integer
    )""")
    conn.sql("""
    create table if not exists llm_temp(flooring_color varchar,
        flooring_color_rgb VARCHAR,
        flooring_material VARCHAR,
        flooring_pattern VARCHAR,
        flooring_design_special_feature VARCHAR,
        flooring_designer_comment VARCHAR,
        cabinet_color VARCHAR,
        cabinet_color_rgb VARCHAR,
        cabinet_material VARCHAR,
        cabinet_pattern VARCHAR,
        cabinet_design_special_feature VARCHAR,
        cabinet_designer_comment VARCHAR,
        countertop_color VARCHAR,
        countertop_color_rgb VARCHAR,
        countertop_material VARCHAR,
        countertop_pattern VARCHAR,
        countertop_design_special_feature VARCHAR,
        countertop_designer_comment VARCHAR,
        page VARCHAR,
        image_url VARCHAR)"""
    )
    conn.sql("""
    create table if not exists hz_llm(plink varchar,
        region VARCHAR,
        page VARCHAR,
        psrc VARCHAR,
        image_size VARCHAR,
        flooring_color VARCHAR,
        flooring_color_rgb VARCHAR,
        flooring_material VARCHAR,
        flooring_pattern VARCHAR,
        flooring_design_special_feature VARCHAR,
        flooring_designer_comment VARCHAR,
        cabinet_color VARCHAR,
        cabinet_color_rgb VARCHAR,
        cabinet_material VARCHAR,
        cabinet_pattern VARCHAR,
        cabinet_design_special_feature VARCHAR,
        cabinet_designer_comment VARCHAR,
        countertop_color VARCHAR,
        countertop_color_rgb VARCHAR,
        countertop_material VARCHAR,
        countertop_pattern VARCHAR,
        countertop_design_special_feature VARCHAR,
        countertop_designer_comment VARCHAR)"""
    )


#  안씀. 이미지는 유알엘만
def create_image_dir(path):
    dir_path = Path(path)
    if dir_path.exists()==False:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

# save images to folder/index_number 
def save_image(url,path):
    response = requests.get(url)
    img_file_name = url.split('/')[-1]
    dir_path = Path(path)
    if response.status_code == 200:
        filename = dir_path / img_file_name
        with open(filename, 'wb') as file:
            file.write(response.content)
# 1 paging 
async def crawl_main(urls_list):
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(
            urls=urls_list,
            config=CrawlerRunConfig(stream=False)
        )
        for result in results:
            if result.success:
                page_number = result.url.split('=')[-1]
                internal_links = result.links.get("internal", [])
                #external_links = result.links.get("external", [])
                internal_links_kitchen = [(h["href"],h["text"].replace("Save Photo","")) for h in internal_links if 'www.houzz.com/photos' in h["href"] and 
                     'kitchen' in h["href"] and 
                     'phvw-vp' in h["href"]
                    ]
                media_links = result.media.get("images",[])
                media_links_kitchen = [(h["src"],h["desc"].replace("Save Photo","")) for h in media_links if 'st.hzcdn.com/' in h["src"] and 
                     'Save Photo' in  h["desc"]
                    ]

                print(f"Found photo links {len(internal_links_kitchen)} internal_links_kitchen.")
                #print(f"Found {len(internal_links)} external links.")
                print(f"Found {len(media_links_kitchen)} media items.")
                # 
                image_url_only = [i[0] for i in media_links_kitchen]
                big_image_only = [i for i in image_url_only if 'w720-h720' in i] # gem limit 10
                #[save_image(u,image_path) for u in image_url_only]

                l_df = pd.DataFrame(internal_links_kitchen, columns=["plink","ptext"])
                l_df["page"]=page_number
                hzdb.sql("insert into hz_links_temp select * from l_df")

                i_df = pd.DataFrame(media_links_kitchen, columns=["psrc","pdesc"])
                i_df["page"]=page_number
                hzdb.sql("insert into hz_img_temp select * from i_df")

                # gemini
                gem_start = time.time()
                llm_result = [await process_kitchen_image_by_gemini(client,u,page_number) for u in big_image_only]
                gem_end = time.time()
                print(f"== llm_call {len(big_image_only)} images : running time : {gem_end - gem_start:.5f} sec")
     
                g_df = pd.DataFrame(llm_result)
                print(g_df)
                hzdb.sql("insert into llm_temp select * from g_df")

                #  write final result
                #hzdb.sql(insert_hz_llm)
                #await asyncio.sleep(4)
                # Each link is typically a dictionary with fields like:
                # { "href": "...", "text": "...", "title": "...", "base_domain": "..." }
    #            if internal_links_kitchen:
    #                print("=====================")
    #                print("Sample Internal Link:", internal_links_kitchen)

                #if external_links: 
                #    print("=====================")
                #    print("Sample external_links:", external_links) 

    #            if media_links_kitchen:
    #                print("=====================")
    #                print(media_links_kitchen)

            else:
                print("Crawl failed:", result.error_message) 

if __name__ == "__main__":
    # 시작페이지부터 추출 카운트 
    url_list = [hz_urls+'?pg='+str(i+from_index) for i in range(int(crawl_count/20))]
    create_tables(hzdb)
    #create_image_dir(image_path)
    start = time.time()
    #async for u in url_list:
    asyncio.run(crawl_main(url_list))
    end = time.time()
    print(f"== crawling and llm_call {len(url_list)} pages : running time : {end - start:.5f} sec")  
    hzdb.close()
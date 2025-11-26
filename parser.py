from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
import re

from crawler import Crawler

class Parser:
    def clean_text(self, raw_text: str, way: int = 1) -> str:
        clean_text: str = ""
        
        if way == 1:
            clean_text = " ".join(raw_text.split())
            clean_text = clean_text.replace("관련어휘", "")
        else:
            for text in raw_text.split("\n"):
                if text.strip() and text != "속도조절":
                    clean_text += f"\n{text}"

        return clean_text.strip()
    
    def get_detailed_data(self, html: str) -> Dict[str, Any]:
        data = {
            "pronounce": "",
            "conjugation": "", # (동사의) 활용
            "meaning": "",
            "image_url": ""
        }

        # HTML 파싱
        soup:bs = bs(html, 'html.parser')

        # 발음 기호
        pronounce_items = soup.select("div.component_keyword > div.row > div.listen_global_area > div.pronounce_area")
        for item in pronounce_items:
            if item:
                pronounce_item_text:str = self.clean_text(item.text)
                data["pronounce"] += f"## pronounce\n"
                data["pronounce"] += f"{pronounce_item_text}\n"

        conjugation = soup.find("dl", {"class": "entry_conjugation"}) # 활용 (부표제어 및 발음)
        if conjugation:
            conjugation_text: str = self.clean_text(conjugation.text, way=0)
            data["conjugation"] += f"## conjugation\n"
            data["conjugation"] += f"{conjugation_text}\n"

        part_area: List = soup.find_all("div", {"class": "part_area"}) # 품사 분류
        mean_list: List = soup.select("#content > div.article > div.section > div > div.mean_tray > ul") # 품사별 의미 목록

        for i in range(len(mean_list)):
            try:
                part_area_text: str = self.clean_text(part_area[i].text) # 품사
                data["meaning"] += f"## part area\n"
                data["meaning"] += f"{part_area_text}\n"
            except: pass

            items: List = mean_list[i].find_all("li", {"class": "mean_item"})
            for item in items:
                number = item.find("span", {"class":"num"}) # 번호
                if number:
                    number_text: str = self.clean_text(number.text)
                    data["meaning"] += f"## number\n"
                    data["meaning"] += f"{number_text}\n"

                part_speech_list = item.find_all("em", {"class":"part_speech"}) # 영영풀이/품사
                if part_speech_list:
                    for part_speech in part_speech_list:
                        part_speech_text: str = self.clean_text(part_speech.text)
                        data["meaning"] += f"## part speech\n"
                        data["meaning"] += f"{part_speech_text}\n"

                mean_addition = item.find("span", {"class":"mean_addition"}) # 의미 부연 설명
                if mean_addition:
                    mean_addition_text: str = mean_addition.text.strip()
                    data["meaning"] += f"## mean addition\n"
                    data["meaning"] += f"{mean_addition_text}\n"

                mean = item.find("span", {"class":"mean"}) # 의미
                if mean:
                    mean_text: str = mean.text.strip()
                    data["meaning"] += f"## mean\n"
                    data["meaning"] += f"{mean_text}\n"

                example_item = item.find("div", {"class":"example_item"}) # 예문
                if example_item:
                    example_item_text: str = self.clean_text(example_item.text, way=0)
                    data["meaning"] += f"## example\n"
                    data["meaning"] += f"{example_item_text}\n"

                reference = item.find("div", {"class":"reference"}) # 문형
                if reference:
                    reference_text: str = self.clean_text(reference.text)
                    data["meaning"] += f"## reference\n"
                    data["meaning"] += f"{reference_text}\n"

                component_relation = item.find("ul", {"class":"component_relation"}) # 유의어/반의어
                if component_relation:
                    component_relation_text: str = self.clean_text(component_relation.text)
                    data["meaning"] += f"## component relation\n"
                    data["meaning"] += f"{component_relation_text}\n"

        image = soup.find("div", {"class":"thumb"}) # 이미지
        if image:
            raw_style = image.get("style")  # 타입: _AttributeValue | None

            # 타입 정리
            if isinstance(raw_style, list):
                style_attr: str = " ".join(raw_style)
            elif isinstance(raw_style, str):
                style_attr = raw_style
            else:
                style_attr = ""

            # 정규식 검색
            match: Optional[re.Match[str]] = re.search(r"url\(['\"]?(.*?)['\"]?\)", style_attr)
            if match:
                image_url: str = match.group(1)
                data["image_url"] = image_url
        
        return data

if __name__ == "__main__":
    input_words = [
        "water",
        "pace",
        "inquire",
        "bark",
        "bat",
        "row",
    ]

    result_lst = []
    crawler = Crawler()
    for word in input_words:
        result = crawler.search_from_naver(word)
        result_lst.append(result)
    
    parser = Parser()
    for htmls in result_lst:
        print("--- --- ---")
        for html in htmls:
            parsed_data = parser.get_detailed_data(html)
            print(parsed_data)
            print()
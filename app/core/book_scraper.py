import re
from typing import Dict
from dotenv import load_dotenv
import os
import json
from app.tool import clean_text, extract_chapter_id_and_name
from tqdm import tqdm
import time
from DrissionPage import Chromium
from DrissionPage.items import ChromiumElement

load_dotenv()


class QidianBookScraper:

    chrome: Chromium = None

    def __init__(self, book_id: str):
        self.book_id = book_id
        self.base_url = "https://www.qidian.com"
        self.data_dir = f"data/book/{book_id}"
        self.html_path = f"{self.data_dir}/{self.book_id}.html"
        
    def get_book_content(self) -> bool:
        """获取书籍内容"""
        if os.path.exists(self.html_path):
            return self.html_path
        self.chrome = Chromium()
        try:
            url = f"{self.base_url}/book/{self.book_id}/"
            tab = self.chrome.new_tab()
            tab.get(url)
            
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.html_path, "w", encoding="utf-8") as f:
                f.write(tab.html)
            tab.close()
            if not (self._extract_free_chapters() and self._get_chapter_content()):
                return False
            return True
        except Exception as e:
            print(e)
            return False

    def _extract_free_chapters(self) -> bool:
        """从HTML文件中提取免费章节信息"""

        if os.path.exists(f"{self.data_dir}/{self.book_id}.json"):
            return True
        try:
            with open(self.html_path, "r", encoding="utf-8") as file:
                soup = BeautifulSoup(file.read(), "html.parser")

            volume_chapters = soup.find("ul", class_="volume-chapters")
            if not volume_chapters:
                return False

            chapters = []
            for item in volume_chapters.find_all("li", class_="chapter-item"):
                link = item.find("a", class_="chapter-name")
                if link:
                    href = link.get("href")
                    title = clean_text(link.get_text(strip=True))
                    chapter_id, chapter_name = extract_chapter_id_and_name(title)
                    
                    if href and href.startswith("//"):
                        href = "https:" + href

                    chapters.append({
                        "id": chapter_id,
                        "name": chapter_name,
                        "url": href
                    })

            os.makedirs(self.data_dir, exist_ok=True)
            json_path = f"{self.data_dir}/{self.book_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(chapters, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(e)
            return False

    def _get_chapter_content(self) -> bool:
        """获取每一章的详细内容"""
        if os.path.exists(f"{self.data_dir}/list/.completed"):
            return True
        try:
            json_path = f"{self.data_dir}/{self.book_id}.json"
            with open(json_path, "r", encoding="utf-8") as file:
                chapters = json.load(file)

            for index, chapter in tqdm(enumerate(chapters), desc="获取章节内容"):
                if chapter["url"]:
                    tab = self.chrome.new_tab()
                    tab.get(chapter["url"])
                    soup = BeautifulSoup(tab.html, "html.parser")
                    tab.close()
                    main_content = soup.find("main", id=lambda x: x and x.startswith("c-"))
                    if not main_content:
                        print(f"未找到章节内容: {chapter['name']}")
                        continue

                    content_dir = f"{self.data_dir}/list"
                    os.makedirs(content_dir, exist_ok=True)
                    with open(f"{content_dir}/{index}.txt", "w", encoding="utf-8") as file:
                        file.write("\n".join(p.get_text() for p in main_content.find_all("p")))
                    
                    time.sleep(0.5)
            return True
        except Exception as e:
            print(e)
            return False

class FQBookScraper:

    def __init__(self, book_id: str,arguments:str):
        self.book_id = book_id
        self.base_url = "https://kol.fanqieopen.com/page/book-detail"
        self.data_dir = f"data/book/{book_id}"
        self.arguments = arguments

    def get_book_content(self) -> bool:
        """获取书籍内容"""
        if os.path.exists(f"{self.data_dir}/list/.completed"):
            return True
        self.chrome = Chromium()
        try:
            url = f"{self.base_url}?book_id={self.book_id}{self.arguments}"
            tab = self.chrome.new_tab()
            tab.get(url)
            
            os.makedirs(self.data_dir, exist_ok=True)
            mulus = tab.ele("@class:catalogue__list").children()
            mulus = [item for item in mulus if "catalogue__item--disable" not in item.attr("class")]
            contents = []
            for i in range(len(mulus)):
                mulus = tab.ele("@class:catalogue__list").children()
                mulus:list[ChromiumElement] = [item for item in mulus if "catalogue__item--disable" not in item.attr("class")]
                mulus[i].click()
                contents.append(tab.ele("#content").text)
                time.sleep(1)
            content_dir = f"{self.data_dir}/list"
            os.makedirs(content_dir, exist_ok=True)
            for i, content in enumerate(contents):
                with open(f"{content_dir}/{i}.txt", "w", encoding="utf-8") as file:
                    file.write(content)
            tab.close()
            with open(f"{self.data_dir}/list/.completed", "w", encoding="utf-8") as f:
                f.write("done")
            return True
        except Exception as e:
            print(e)
            return False


if __name__ == "__main__":
    scraper = QidianBookScraper("1043599413")
    if scraper.get_book_content():
        if scraper.extract_free_chapters(f"{scraper.data_dir}/{scraper.book_id}.html"):
            scraper.get_chapter_content()
    else:
        print("获取书籍内容失败")

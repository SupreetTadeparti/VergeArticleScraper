from collections import defaultdict
from colorama import Fore, Style
from dataclasses import dataclass
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
import sqlite3


@dataclass
class ArticleData:
    url: str
    headline: str
    author: str
    date: str

    def get_list(self):
        return [self.url, self.headline, self.author, self.date]


class VergeScraper:
    MONTHS = {
        "Jan": "01",
        "Feb": "02",
        "Mar": "03",
        "Apr": "04",
        "May": "05",
        "Jun": "06",
        "Jul": "07",
        "Aug": "08",
        "Sep": "09",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12"
    }

    def __init__(self) -> None:
        self.driver = Firefox()

    def __del__(self) -> None:
        self.driver.quit()

    def scrape_article(self, url: str) -> ArticleData:
        self.driver.get(url)

        # HEADLINE ------------

        # there seems to be two types of articles, with different selectors for the headline.

        headlineElements = self.driver.find_elements(
            by=By.CSS_SELECTOR, value=".duet--article--feature-headline")

        headlineEl = None

        if len(headlineElements) == 0:
            headlineEl = self.driver.find_element(
                by=By.CSS_SELECTOR, value="h1.mb-28"
            )
        else:
            headlineEl = headlineElements[0]

        headline = "\"" + \
            headlineEl.text.replace("’", "'").replace("—", "-") + "\""

        # ---------------------

        # TIME ----------------

        timeElements = self.driver.find_elements(
            by=By.CSS_SELECTOR, value=".duet--article--timestamp"
        )

        # skip storing article if date cannot be found
        if len(timeElements) == 0:
            print(Fore.LIGHTRED_EX + "SKIPPING ARTICLE: " + headline)
            print(Style.RESET_ALL)
            return None

        timeEl = timeElements[0]

        # Convert "Month Day, Year, time..." to "mm/dd/yyyy"
        date = "/".join([x.zfill(2) if x not in self.MONTHS else self.MONTHS[x]
                        for x in "".join(timeEl.text.replace("Updated", "").strip().split(",")[:2]).split(" ")])

        # ---------------------

        # AUTHOR --------------

        authorEl = self.driver.find_element(
            by=By.CSS_SELECTOR, value="span.font-medium:nth-child(2) > a:nth-child(1)"
        )

        # change from uppercase to capitalized. i.e. "LOREM IPSUM" to "Lorem Ipsum"
        author = " ".join([name.capitalize()
                          for name in authorEl.text.split(" ")])

        # ---------------------

        print(Fore.GREEN + "SCRAPED ARTICLE: " + headline)
        print(Style.RESET_ALL)

        return ArticleData(url, headline, author, date)

    def scrape_top_articles(self) -> list[ArticleData]:
        self.driver.get("https://www.theverge.com/")

        top_articles = self.driver.find_elements(
            by=By.CSS_SELECTOR, value="ol.relative > li > div > .flex > div > h2 > a")

        top_article_urls = []

        for article in top_articles:
            href = article.get_attribute("href")
            if href is not None:
                top_article_urls.append(href)

        data = [self.scrape_article(url) for url in top_article_urls]

        # remove incompatible articles
        data = [article for article in data if article is not None]

        return data

    def scrape_all_articles(self) -> dict[str, list[ArticleData]]:
        self.driver.get("https://www.theverge.com/archives/1")

        articles = self.driver.find_elements(
            by=By.CSS_SELECTOR, value=".duet--content-cards--content-card.z-10 .font-bold > a")

        urls = [article.get_attribute("href") for article in articles]

        data = defaultdict(list)

        for url in urls:
            article_data = self.scrape_article(url)

            # skip incompatible articles
            if article_data is None:
                continue

            data[article_data.date].append(article_data)

        return data


class ArticleStorage:
    def __init__(self, data: dict[str, list[ArticleData]]):
        self.data = data

    def write_to_csv(self) -> None:
        for date in self.data:
            data = self.data[date]
            with open(date.replace("/", "") + "_verge.csv", "w") as file:
                file.write("ID,URL,Headline,Author,Date\n")
                for idx, line in enumerate(data):
                    file.write(str(idx) + "," + ",".join(line.get_list()) +
                               ("\n" if idx != len(data) - 1 else ""))

    def write_to_sqlite(self) -> None:
        con = sqlite3.connect("article.db")
        db = con.cursor()

        db.execute("""
            CREATE TABLE Article (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                HEADLINE VARCHAR(100) NOT NULL,
                AUTHOR VARCHAR(30) NOT NULL,
                DATE VARCHAR(8) NOT NULL
            );
        """)

        con.commit()

        articles = [article for articles in self.data.values()
                    for article in articles]

        for article in articles:
            headline = article.headline.replace('\'', '\'\'')

            db.execute(f"""
                INSERT INTO Article (HEADLINE, AUTHOR, DATE) 
                VALUES ({headline}, "{article.author}", "{article.date}");
            """)

            con.commit()

        db.close()

from verge_scraper import VergeScraper, ArticleStorage


def main():
    scraper = VergeScraper()

    data = scraper.scrape_all_articles()

    del scraper

    storer = ArticleStorage(data)

    storer.write_to_csv()
    storer.write_to_sqlite()


if __name__ == "__main__":
    main()

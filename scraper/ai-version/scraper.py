# AI-Generated Version (Quarantine folder for Assignment A9: Bonus AI Rematch)
# Notice Flaw 1: No disk caching -> hammers the server every run
# Notice Flaw 2: No User-Agent header (default python-requests user-agent)
# Notice Flaw 3: No error handling on individual pages -> crashes on any broken link!
# Notice Flaw 4: Missing rate-limiting delay (violates politeness)

import requests
from bs4 import BeautifulSoup
import json

def scrape_books():
    books = []
    base_url = "https://books.toscrape.com/catalogue/"
    
    # AI looped naively through pages
    for page in range(1, 4):
        url = f"{base_url}page-{page}.html"
        r = requests.get(url)  # No timeout!
        soup = BeautifulSoup(r.text, "html.parser")
        
        for item in soup.select("article.product_pod"):
            book_rel = item.select_one("h3 > a")["href"]
            book_url = f"{base_url}{book_rel}"  # Brittle string concatenation instead of urljoin
            
            # Flaw: unhandled request will throw exception and kill the entire script!
            detail_res = requests.get(book_url)
            detail_soup = BeautifulSoup(detail_res.text, "html.parser")
            
            title = detail_soup.select_one("h1").text
            price = detail_soup.select_one("p.price_color").text
            
            books.append({
                "title": title,
                "price": price,
                "url": book_url
            })
            
    with open("books.json", "w") as f:
        json.dump(books, f)

if __name__ == "__main__":
    scrape_books()

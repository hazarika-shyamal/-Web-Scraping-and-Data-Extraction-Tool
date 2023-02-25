import argparse
import json
import requests
from bs4 import BeautifulSoup
import PyPDF2
import re
import time
import requests


def extract_pdf_text(data):
    pdf_reader = PyPDF2.PdfFileReader(data)
    text = ""
    for i in range(pdf_reader.getNumPages()):
        page = pdf_reader.getPage(i)
        text += page.extractText()
    return text


def handle_connection_error(url, headers, proxies):
    retry_count = 0
    max_retries = 3
    delay = 2

    while retry_count < max_retries:
        try:
            response = requests.get(url, headers=headers, proxies=proxies)
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout as e:
            print(f"Request timed out: {e}. Retrying in {delay} seconds...")
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}. Retrying in {delay} seconds...")
        except requests.exceptions.RequestException as e:
            print(f"Error during request: {e}. Retrying in {delay} seconds...")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                print(f"Page not found: {e}.")
            elif response.status_code == 500:
                print(f"Server error: {e}.")
            else:
                print(f"HTTP error: {e}.")
        time.sleep(delay)
        retry_count += 1
    raise Exception("Failed to connect after maximum number of retries")


def scrape_data(url, user_agent, proxies):
    headers = {"User-Agent": user_agent}
    response = handle_connection_error(url, headers, proxies)
    if response.headers["content-type"] == "text/html":
        soup = BeautifulSoup(response.content, "html.parser")
        # Extract data from HTML page
        links = [a["href"] for a in soup.find_all("a")]
        filtered_links = filter_links(links, r'(https?://\S+)')
        return filtered_links
    elif response.headers["content-type"] == "application/json":
        json_data = response.json()
        # Extract data from JSON response
        return json_data
    elif response.headers["content-type"] == "text/plain":
        # Extract data from plain text response
        return response.text
    elif response.headers["content-type"] == "image/jpeg":
        # Extract data from JPEG image
        return response.content
    elif response.headers["content-type"] == "image/png":
        # Extract data from PNG image
        return response.content
    elif response.headers["content-type"] == "application/pdf":
        # Extract data from PDF document
        return extract_pdf_text(response.content)
    else:
        raise Exception("Unsupported content type")


def filter_links(links, pattern):
    filtered_links = [link for link in links if re.match(pattern, link)]
    return filtered_links


def save_data(data, filename, mode='w'):
    try:
        with open(filename, 'w') as file:
            file.write(data)
    except Exception as e:
        print(f"Error occurred while saving data to file: {str(e)}")


def scrape_pages(urls, user_agent, proxies):
    for url in urls:
        page_data = get_page_data(url, user_agent, proxies)
        data_type = input(
            "Enter the type of data to extract from the page (links, paragraphs, headings, images, pdf): ")
        scraped_data = data_from_page(page_data, data_type)
        print(scraped_data)
        links = scrape_data(url, user_agent, proxies)
        print(links)
        filename = "filtered_links.json"
        save_data(filename, links, mode='w')


def get_page_data(url, user_agent, proxies):
    headers = {'User-Agent': user_agent}
    response = requests.get(url, headers=headers, proxies=proxies)
    content_type = response.headers['content-type']
    if 'text/html' in content_type:
        return BeautifulSoup(response.content, 'html.parser')
    elif 'application/pdf' in content_type:
        return response.content
    else:
        raise Exception('Unsupported content type')


def data_from_page(page_data, data_type):
    if data_type == 'links':
        links = [a['href'] for a in page_data.find_all('a')]
        filtered_links = filter_links(links, "example.com")
        return filtered_links
    elif data_type == 'paragraphs':
        paragraphs = extract_tag_data(str(page_data), 'p')
        return paragraphs
    elif data_type == 'headings':
        headings = extract_tag_data(
            str(page_data), 'h1') + extract_tag_data(str(page_data), 'h2')
        return headings
    elif data_type == 'images':
        images = [img['src'] for img in page_data.find_all('img')]
        return images
    elif data_type == 'pdf':
        pdf_data = extract_pdf_text(page_data)
        return pdf_data
    else:
        raise Exception('Unsupported data type')


def extract_tag_data(html_data, tag_name):
    soup = BeautifulSoup(html_data, 'html.parser')
    tag_data = []
    for tag in soup.find_all(tag_name):
        tag_data.append(tag.text)
    return tag_data


def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error occurred: {str(e)}")
    return wrapper


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--output", default="data..txt", help="Output file")
    parser.add_argument(
        "--user_agent", default="Mozilla/5.0 (Windows NT 10.0; Win64; x64)", help="User agent string")
    parser.add_argument(
        "--proxy", help="Proxy server address (e.g. http://<user>:<pass>@<ip>:<port>)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    url = args.url
    output_file = args.output
    user_agent = args.user_agent
    proxy = args.proxy

    proxies = {"http": proxy, "https": proxy} if proxy else None

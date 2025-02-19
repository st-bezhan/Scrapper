from argparse import ArgumentParser
from typing import List, Optional, Sequence
import xml.etree.ElementTree as ET
import html
import requests
import re
import json as json_module


class UnhandledException(Exception):
    pass


class RSSParseError(UnhandledException):
    pass


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                  ' AppleWebKit/537.36'
                  ' (HTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    # This regex matches anything between < and >
    clean = re.compile(r'<[^>]+>')
    return re.sub(clean, '', text)


def parse_xml(xml: str):
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        raise RSSParseError(e)
    channel = root.find("channel")
    if channel is None:
        raise RSSParseError("No <channel> element found.")
    return channel


# Helper function to extract feed data
def extract_feed_data(channel) -> dict:
    return {
        "title": channel.findtext("title", ""),
        "link": channel.findtext("link", ""),
        "lastBuildDate": channel.findtext("lastBuildDate", ""),
        "pubDate": channel.findtext("pubDate", ""),
        "language": channel.findtext("language", ""),
        "managingEditor": channel.findtext("managingEditor", ""),
        "description": channel.findtext("description", ""),
        "category": [cat.text for cat in channel.findall("category") if
                     cat.text]
    }


# Helper function to filter items by category
def filter_by_category(items, category: str):
    return [item for item in items if
            category in item.findtext("category", "")]


# Helper function to apply limit to the items
def apply_limit(items, limit: Optional[int]):
    return items[:limit] if limit is not None else items


# Helper function to extract plain item data
def extract_item_data(item) -> dict:
    return {
        "title": item.findtext("title", ""),
        "author": item.findtext("author", ""),
        "pubDate": item.findtext("pubDate", ""),
        "link": item.findtext("link", ""),
        "category": item.findtext("category", ""),
        "description": strip_html_tags(
            html.unescape(item.findtext("description", ""))),
    }


# Helper function to convert data to JSON
def convert_to_json(feed_data: dict, plain_items: List[dict]) -> List[str]:
    def clean_dict(d):
        return {k: v for k, v in d.items() if v not in [None, "", []]}

    feed_data_json = {}
    for key in ["title", "link", "lastBuildDate", "pubDate", "language",
                "managingEditor", "description", "category"]:
        val = feed_data.get(key)
        if val not in [None, "", []]:
            feed_data_json[key] = val

    if plain_items:
        items_clean = [clean_dict(item) for item in plain_items if
                       clean_dict(item)]
        if items_clean:
            feed_data_json["items"] = items_clean

    return [json_module.dumps(feed_data_json, indent=2, ensure_ascii=False)]


# Helper function to format plain text output
def format_plain_text(feed_data: dict, plain_items: List[dict]) -> List[str]:
    lines = []
    lines.append(f"Feed:{feed_data['title']}")
    lines.append(f"Link:{feed_data['link']}")
    if feed_data.get("lastBuildDate"):
        lines.append(f"LastBuildDate:{feed_data['lastBuildDate']}")
    if feed_data.get("pubDate"):
        lines.append(f"PublishDate:{feed_data['pubDate']}")
    if feed_data.get("language"):
        lines.append(f"Language:{feed_data['language']}")
    if feed_data.get("category"):
        lines.append(f"Categories:{','.join(feed_data['category'])}")
    if feed_data.get("managingEditor"):
        lines.append(f"Editor:{feed_data['managingEditor']}")
    lines.append(f"Description:{feed_data['description']}")

    if plain_items:
        lines.append("")

    for item in plain_items:
        lines.append(f"\nTitle:{item.get('title', '')}")
        if item.get("author"):
            lines.append(f"Author:{item['author']}")
        if item.get("pubDate"):
            lines.append(f"Published:{item['pubDate']}")
        lines.append(f"Link:{item.get('link', '')}")
        if item.get("category"):
            lines.append(f"Categories:{item['category']}")
        if item.get("description"):
            lines.append("")
            lines.append(strip_html_tags(item["description"]))

    return lines


def rss_parser(
        xml: str,
        limit: Optional[int] = None,
        json: bool = False, category: str = None
) -> List[str]:
    """
    RSS parser.

    Args:
        xml: XML document as a string.
        limit: Number of the news to return. if None, returns all news.
        json: If True, fomat output as JSON.
        category: Optional category for filtering

    Returns:
        List of strings.
        Which then can be printed to stdout or written to file
        as a separate lines.

    Examples:
        >>> xml_ = '<rss><channel><title>Some RSS Channel</title>' +
        '<link>https://some.rss.com</link>' +
        '<description>Some RSS Channel</description></channel></rss>'
        >>> rss_parser(xml_)
        ["Feed: Some RSS Channel",
        "Link: https://some.rss.com"]
        >>> print("\\n".join(rss_parser(xml_)))
        Feed: Some RSS Channel
        Link: https://some.rss.com
    """
    # Your code goes here
    channel = parse_xml(xml)
    feed_data = extract_feed_data(channel)
    items = channel.findall("item")

    # Apply the category filter if provided
    if category:
        items = filter_by_category(items, category)

    # Apply the limit if provided
    items = apply_limit(items, limit)

    # Extract item data
    plain_items = [extract_item_data(item) for item in items]
    feed_data["items"] = plain_items

    # Return JSON or plain text
    if json:
        return convert_to_json(feed_data, plain_items)
    else:
        return format_plain_text(feed_data, plain_items)


def main(argv: Optional[Sequence] = None):
    """
    The main function of your task.
    """
    parser = ArgumentParser(
        prog="rss_reader",
        description="Pure Python command-line RSS reader.",
    )
    parser.add_argument("source", help="RSS URL", type=str, nargs="?")
    parser.add_argument(
        "--json", help="Print result as JSON in stdout", action="store_true"
    )
    parser.add_argument(
        "--limit", help="Limit news topics if this parameter provided",
        type=int
    )
    parser.add_argument(
        "--category", help="Filter news topics by category.",
        type=str
    )

    args = parser.parse_args(argv)
    xml = requests.get(args.source, headers=headers).text
    try:
        print("\n".join(rss_parser(xml, args.limit, args.json, args.category)))
        return 0
    except Exception as e:
        raise UnhandledException(e)


if __name__ == "__main__":
    main()

from bs4 import BeautifulSoup
from test_data import theridion_synonyms, theridion_transfers, idiothele_synonyms
from functions import split_taxref_items, parse_synonym_item

soup = BeautifulSoup(idiothele_synonyms)
items = split_taxref_items(soup)
parsed_items = []
for item in items:
  parsed_item = parse_synonym_item(item)
  parsed_items.append(parsed_item)


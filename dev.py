# just for running various bits of code...
from enum import Enum
import csv
from functions import get_genus_page_soup, \
get_main_divs, get_divs_following_genus_title, \
get_target_taxref, split_taxref_items, \
parse_transfer_item, parse_synonym_item, parse_taxref_list

#different genera for testing
#url = 'genus/278' #Araneus
#url = 'genus/3550' #Theridion
url = 'genus/502' #Clubiona
#url = 'genus/3374' #Idiothele

out_filename = 'clubiona_synonyms.csv'

class Sections(Enum):
  SYNONYMS = "In synonymy"
  TRANSFERS = "Transferred to other genera"
  HOMONYMS = "Homonyms replaced"
  NOMDUBS = "Nomina dubia"
  NOMNUDS = "Nomina nuda"
  # Not sure whether there are any (sub)species inquirenda

parseFunctions = {
  "SYNONYMS": parse_synonym_item,
  "TRANSFERS": parse_transfer_item
}

print('fetching WSC page...')
genus_page = get_genus_page_soup(url)

main_divs = get_main_divs(genus_page)
if not main_divs:
  print('Oops! No divs to work with...')
  exit()

top_sections = get_divs_following_genus_title(main_divs)
if not top_sections:
  print('Oops! No taxrefs to work with...')
  exit()


taxref = get_target_taxref(top_sections, Sections.SYNONYMS.value)
item_list = split_taxref_items(taxref)

print('parsing synonyms...')
synonyms = parse_taxref_list(item_list, parseFunctions[Sections.SYNONYMS.name])

with open(out_filename, 'w', encoding='utf8', newline='', errors='ignore') as csvfile:
  writer = csv.DictWriter(csvfile, fieldnames=synonyms[0].keys(), )
  writer.writeheader()
  writer.writerows(synonyms)

print('all done...')




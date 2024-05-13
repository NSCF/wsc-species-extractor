import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from nanoid import generate

def nanoid():
  return generate('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', 16)


base_url = 'https://wsc.nmbe.ch'
gnparser_url = 'https://parser.globalnames.org/api/v1'

def get_family_urls(families_table_url):
  families_url = urljoin(base_url, families_table_url)
  families_page = requests.get(families_url)
  families_soup = BeautifulSoup(families_page.content, "html.parser")
  families_main = families_soup.find('main')
  families_table = families_main.find('table')
  families_table_body = families_table.find('tbody')
  families_table_rows = families_table_body.find_all('tr')
  
  family_urls = {}
  for families_table_row in families_table_rows:
    family_name_td = families_table_row.find('td')
    family_name = family_name_td.find('strong').text
    family_url_elem = families_table_row.find(title="Genera list")
    family_url = family_url_elem['href']
    family_urls[family_name] = family_url
  
  return family_urls


def get_genus_page_urls(family_page_url):
  family_page = requests.get(urljoin(base_url, family_page_url))
  family_soup = BeautifulSoup(family_page.content, 'html.parser')
  family_main_elem = family_soup.find('main') 
  genera_table = family_main_elem.find('table')
  genera_table_body = genera_table.find('tbody')
  genera_table_rows = genera_table_body.find_all('tr')
  
  genus_page_urls = {}
  for genus_row in genera_table_rows:
    genus_name_td = genus_row.find('td')
    genus_name = genus_name_td.find('strong').text
    genus_url_elem = genus_row.find(title="Show species entries")
    genus_page_url = genus_url_elem['href']
    genus_page_urls[genus_name] = genus_page_url

  return genus_page_urls

def get_genus_page_soup(genus_page_url):
  genus_page = requests.get(urljoin(base_url, genus_page_url))
  genus_page_soup = BeautifulSoup(genus_page.content, 'html.parser')
  return genus_page_soup

def check_genus_page_match(genus_name, genus_page_soup):
  genus_page_main = genus_page_soup.find('main')
  page_genus_name_elem =  genus_page_main.find(class_="genusTitle")
  page_genus_name = page_genus_name_elem.find('strong').text
  
  return page_genus_name == genus_name
  

def parse_species_title(species_title_elem):
  species_name = species_title_elem.find('strong').text
  a_elem = species_title_elem.find('a')
  a_sibling = a_elem.next_sibling
  while len(a_sibling.text.strip()) == 0:
    a_sibling = a_sibling.next_sibling
  species_author = a_sibling.text.strip()
  species_lsid = re.findall(r'\[(.+)\]', species_title_elem.text)[0]
  return { 
    "taxonID": nanoid(), 
    "acceptedNameID": None, 
    "name": species_name, 
    "author": species_author,
    "hasDescription": None, 
    "lsid": species_lsid, 
    "fullref": None
  }


def get_species_synonyms(species_name, speciesID, species_taxref_elem):
  
  # the individual references are not elements on their own, so we have to split on <br>
  refs = []
  refstring = ''
  for item in species_taxref_elem.contents:
    if '<br/>' in str(item):
      soup = BeautifulSoup(refstring.strip(), 'html.parser')
      refs.append(soup)
      refstring = ''
    else:
      refstring += str(item)

  # assume that the first instance of a name that is different to the species name is the origin of that name, and therefore a synonym
  # note that this will miss homonyms :-/
  synonyms = {}
  for ref in refs:
    ref_name = ref.find('i').text
    if ref_name != species_name and ref_name not in synonyms:

      ref_content = ref.text.split(':')[1]

      #these are also not synonyms
      if 'misidentified' in ref_content.lower():
        continue
      
      has_description = False
      if 'D' in ref_content:
        has_description = True
      
      ref_source = ref.find('strong').text

      #sometimes we have authors in sources, which we need to fix
      source_parts = ref_source.split(',')
      author_parts = list(filter(lambda x: ' in ' not in x, source_parts))
      ref_author = ','.join(author_parts)
      ref_author = re.sub(r',(?=[^,]*$)', '', ref_author) # replace the last comma, which we added above
      ref_author = re.sub("[a-z]+$", '', ref_author)

      # and sometimes we have lsids
      synonym_lsid = None
      lsids = re.findall(r'\[(.+)\]', ref.text)
      if len(lsids) > 0:
        synonym_lsid = lsids[0]

      synonyms[ref_name] = {
        "taxonID": nanoid(), 
        "acceptedNameID": speciesID,
        "name": ref_name, 
        "author": ref_author, 
        "hasDescription": has_description,
        "lsid": synonym_lsid,
        "fullref": ref_content
      }
    
  return synonyms.values()

def get_species_and_synonyms(genus_page_soup):
  genus_page_main = genus_page_soup.find('main')
  # we need to iterate over divsonly, because we don't want the white space between them (which are technically sibling nodes)
  next_species_elem = genus_page_main.find('div', class_='speciesTitle')
  species_records = []
  while next_species_elem is not None:
    
    species_data = parse_species_title(next_species_elem)
    species_records.append(species_data)

    next_species_detail = next_species_elem.find_next_sibling('div')
    synonyms = get_species_synonyms(species_data["name"], species_data['taxonID'], next_species_detail)
    species_records += synonyms

    next_species_elem = next_species_detail.find_next_sibling('div')

  return species_records



  





import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from nanoid import generate

# TODO replace with simple integer counters...
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

def get_main_divs(genus_page_soup):
  """Get the divs in the main section of the page, which contain the taxrefs and genus/species title sections"""
  genus_page_main = genus_page_soup.find('main')
  box = genus_page_main.find('div', class_ = 'ym-wbox')
  divs = box.find_all('div')
  return divs

def get_divs_following_genus_title(divs_soup_list):
  """Get the everything after the genus title and before the first species title """

  after_genus_title = []
  reached_genus_title = False
  for div_soup in divs_soup_list:
    if 'genusTitle' in div_soup['class']:
      reached_genus_title = True

    if 'speciesTitle' in div_soup['class']:
      return after_genus_title

    if reached_genus_title:
      after_genus_title.append(div_soup)
  
  return after_genus_title # this shouldn't happen

def get_species_and_chrysonyms_items(genus_page_soup):
  """Get all the species title elements and their list of chrysonyms"""

  genus_page_main = genus_page_soup.find('main')
  # we need to iterate over divs only, because we don't want the white space between them (which are technically sibling nodes)
  species_title_elem = genus_page_main.find('div', class_='speciesTitle') #the first one
  species_records = []
  while species_title_elem is not None:
    species_data = parse_species_title(species_title_elem)
    chrysonyms_elem = species_title_elem.find_next_sibling('div')
    chrysonyms = parse_chrysonyms(species_data["name"], species_data['taxonID'], chrysonyms_elem)
    species_data['chrysonyms'] = chrysonyms
    species_records.append(species_data)
    species_title_elem = chrysonyms_elem.find_next_sibling('div')
  return species_records

### UTILITY FUNCTIONS USED NEXT ###

def split_taxref_items(taxref_soup):
  """Split a taxref into individual synonym/transfer/etc html items"""

  taxref_html = str(taxref_soup)
  
  # splitting and cleaning up
  item_html_list = re.split(r"<br\s*/?>", taxref_html.replace('\n', '')) # breaks with and without ending backslash
  item_html_list = list(map(lambda x: (re.sub(r"\s+", " ", x)).strip(), item_html_list))
  
  # the first item is the heading and the last is a closing div
  item_html_list.pop()
  item_html_list.reverse()
  item_html_list.pop()
  item_html_list.reverse()

  item_soup_list = list(map(lambda html: BeautifulSoup(html, "html.parser"), item_html_list))

  return item_soup_list

def parse_transfer_item(item_soup):
  """For parsing each item under the 'Transferred to other genera' section"""

  name_elem = item_soup.find('i')
  name = name_elem.text
  author_elem = name_elem.next_sibling
  author = author_elem.text.split('--')[0].strip()
  destination_elem = author_elem.next_sibling
  destination = destination_elem.text
  result = {
    "html": str(item_soup),
    "text" : item_soup.text,
    "fullname": name,
    "author": author,
    "transferred_to": destination
  }

  return result

def parse_synonym_item(item_soup):
  """For parsing each item under the 'In Synonymy' section"""
  
  synonym_note  = None
  synonym_source = None
  accepted_name_note = None

  synonym_name_elem = item_soup.find('i')
  synonym_name = synonym_name_elem.text.strip()
  synonym_author_elem = synonym_name_elem.next_sibling
  original_genus = None # this must be used as a flag to tell us that the names might not match because of gender, etc, use stemmed names
  
  if 'T from' in synonym_author_elem.text:
    
    original_genus_elem = synonym_author_elem.next_sibling
    original_genus = original_genus_elem.text
    synonym_author_string = synonym_author_elem.text
    synonym_author_string = synonym_author_string.replace('T from', '').strip()
    synonym_author = re.sub(r',$', '', synonym_author_string) 
    
    if (synonym_author.startswith('(')):
      synonym_author += ')'

  elif 'removed from S of' in synonym_author_elem.text:
    synonym_author = synonym_author_elem.text.replace('removed from S of', '').strip()
    synonym_author = re.sub(r'[,\s\(]+$', '', synonym_author)
    if synonym_author.startswith('(') and not synonym_author.endswith(')'):
      synonym_author += ')'
      
    synonym_note = 'removed from S of '
    while '=' not in synonym_author_elem.text: 
      synonym_author_elem = synonym_author_elem.next_sibling
      synonym_note += synonym_author_elem.text

    synonym_note = re.sub(r'[=?\)?\.?\s]+$', '', synonym_note.strip()).strip()
  
  elif ', sub' in synonym_author_elem.text:
    synonym_author = synonym_author_elem.text.split(', sub')[0].strip()
    if synonym_author.startswith('(') and not synonym_author.endswith(')'):
      synonym_author += ')'
    
    index = synonym_author_elem.text.find(', sub')
    synonym_note = synonym_author_elem.text[index:]
    synonym_author_elem = synonym_author_elem.next_sibling
    synonym_note += synonym_author_elem.text
    while '=' not in synonym_author_elem.text: 
      synonym_author_elem = synonym_author_elem.next_sibling
      synonym_note += synonym_author_elem.text

    synonym_note = re.sub(r'[=?\)?\.?\s]+$', '', synonym_note.strip()).strip()
    synonym_note = re.sub(r"^[,\s]+", "", synonym_note)

  else:
    synonym_author_string = synonym_author_elem.text.replace('=', '').strip() # this can have other stuff still
    synonym_author = synonym_author_string

  accepted_name_elem = synonym_author_elem.find_next_sibling('a')
  accepted_name = accepted_name_elem.text.strip()
  accepted_name_following_elem = accepted_name_elem.next_sibling
  
  if accepted_name_following_elem == item_soup.contents[-1]: #we have cases where we don't have the usual author elements
    elem_text = accepted_name_following_elem.text.strip()
    if elem_text.startswith('('):
      second_paren_index = elem_text.find('(', 1)
      accepted_name_author = elem_text[0:second_paren_index].strip()
      accepted_name_note = re.sub(r'[\)\.\s]+$', '', elem_text[second_paren_index + 1 :])
    else:
      first_paren_index = elem_text.find('(')
      accepted_name_author = elem_text[0:first_paren_index].strip()
      accepted_name_note = re.sub(r'[\)\.\s]+$', '', elem_text[first_paren_index + 1 :])
  else: 
    accepted_name_author = re.sub(r'[\(\s]$', '', accepted_name_following_elem.text).strip()
    synonym_source_elem = accepted_name_following_elem.next_sibling
    
    # we need to add them all up
    synonym_source = ''
    while synonym_source_elem:
      synonym_source += synonym_source_elem.text
      synonym_source_elem = synonym_source_elem.next_sibling
    synonym_source = re.sub(r'[\.\)\s]+$', '', synonym_source)

  if synonym_source: # we can have cases where we don't have this, e.g. Theridion ornatum
    has_note = re.search(r":\s+\d+,\s+", synonym_source)
    if has_note:
      index = synonym_source.find(has_note.group(0))
      note = re.sub(r"[\s\)\.]+$", '', synonym_source[index + len(has_note.group(0)):].strip())
      synonym_source = synonym_source[0:index + len(has_note.group(0))]
      synonym_source = re.sub(r"[,\s]+$", "", synonym_source)

      if accepted_name_note:
        accepted_name_note += '; ' + note
      else:
        accepted_name_note = note

  # lets deal with these Clerkian names
  if '(Clerckian names' in accepted_name_author:
    index = accepted_name_author.find('(Clerckian names')
    if accepted_name_note:
      accepted_name_note += '; ' 
    else:
      accepted_name_note = ""
    accepted_name_note += accepted_name_author[index + 1:] + ' ' + synonym_source + ")" 
    accepted_name_author = accepted_name_author[0: index].strip()
    synonym_source = None

  result = {
    "html": str(item_soup),
    "text": item_soup.text,
    "synonym_name": synonym_name,
    "synonym_author": synonym_author,
    "synonym_note": synonym_note,
    "transferred_from": original_genus,
    "accepted_name": accepted_name,
    "accepted_name_author": accepted_name_author,
    "synonym_source": synonym_source if synonym_source else None,
    "accepted_name_note": accepted_name_note,
  }

  return result

# TODO we also need homonyms, nomina dubia and nomina nuda
def parse_homonym_item(item_soup):
  """For parsing homonyms replaced"""

  #This is identical to transfers...
  name_elem = item_soup.find('i')
  name = name_elem.text
  author_elem = name_elem.next_sibling
  author = author_elem.text.split('--')[0].strip()
  destination_elem = author_elem.next_sibling
  destination = destination_elem.text
  result = {
    "html": str(item_soup),
    "text" : item_soup.text,
    "fullname": name,
    "author": author,
    "replacement_name": destination
  }

  return result

def parse_nomdub_item(item_soup):
  """For parsing nomina dubia"""

  result = {
    "html": None,
    "text": None,
    "fullname": None,
    "author": None,
    
  }

  return result

# TODO add the mf and distribution sections
# TODO add the html and text properties also (for this and chrysonyms)
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

# TODO use split_taxref_items and make this function just do one ref
# TODO use some nice juicy examples from the big families to test
def parse_chrysonyms(species_taxref_elem):
  
  # the individual references are not elements on their own, so we have to split on <br>
  html_refs = str(species_taxref_elem).split('<br/>')
  refs = list(map(lambda html: BeautifulSoup(html, 'html.parser'), html_refs))

  chrysonyms = []
  for ref in refs:
    
    name_elem = ref.find('i')
    ref_name = name_elem.text
    
    ref_source_elem = name_elem.next_sibling
    ref_source = ref_source_elem.text
    
    #sometimes we have authors in sources, which we need to fix
    source_parts = ref_source.split(',')
    author_parts = list(filter(lambda x: ' in ' not in x, source_parts))
    ref_author = ','.join(author_parts)
    ref_author = re.sub(r',(?=[^,]*$)', '', ref_author) # replace the last comma, which we added above
    ref_author = re.sub(r"[a-z]+$", '', ref_author)

    ref_details = ref_source_elem.next_sibling
    ref_details_text = ref_details.text
    next_elem = ref_details.next_element
    while next_elem:
      ref_details_text += next_elem.text
      next_elem = next_elem.next_element

    ref_page = None
    pages = re.search(r'^:\s*(\d+)\b', ref_details_text) 
    if pages:
      ref_page = pages.group(1)
      rest = ref_details_text.replace(pages.group(0), '')
      rest = re.sub(r'^[,\s]+', '', ref_details_text.replace(pages.group(0), ''))
    else:
      rest = re.sub(r'^[,\s]+', '', ref_details_text)
      
    ref_type = None
    ref_type_matches = re.search(r'\((.+)\)', rest)
    if ref_type_matches:
      ref_type = ref_type_matches.group(1)
      rest = rest.replace(ref_type, '')

    guid = None
    guid_matches = re.search(r'\[(.+)\]', rest)
    if guid_matches:
      guid = guid_matches.group(1)
      rest = rest.replace(guid, '')

    # it should only be the illustrations now, after we clean up
    illustrations = re.sub(r'[\[\]\(\)\s]+$', '', rest)

    misidentified = False
    if 'misidentified' in ref_type.lower():
      misidentified = True

    result = {
      "ref_name": ref_name,
      "ref_author": ref_author,
      "ref_source": ref_source,
      "ref_page": ref_page,
      "illustrations": illustrations,
      "ref_type": ref_type,
      "misidentified": misidentified,
      "guid": guid
    }

    chrysonyms.append(result)
    
  return chrysonyms

### MAIN FUNCTIONS ###

def get_target_taxref(tax_refs_soup_list, taxref_header):
  """Gets the synonyms/transfers, etc taxref element for a genus page
  
  Should be provided with the results from get_taxrefs_following_genus_title()
  """

  condition = lambda tax_ref: taxref_header in tax_ref.text

  return next((tax_ref for tax_ref in tax_refs_soup_list if condition(tax_ref)), None)

def parse_taxref_list(taxref_soup_list, parse_function):
  """Parses the provided list of items using parse_function and returns the list of results as dictionaries
  
  Use this to parse transfer, synonyms, etc, before you get to the species and chrysonyms
  """
  results = []
  for soup_item in taxref_soup_list:
    result = parse_function(soup_item)
    results.append(result)
  return results

  



  





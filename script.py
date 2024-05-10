from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

base_url = 'https://wsc.nmbe.ch'
families_url = urljoin(base_url, "families")
print('fetching family list')
families_page = requests.get(families_url)

# fetch the list of families
families_soup = BeautifulSoup(families_page.content, "html.parser")
families_main = families_soup.find('main')
families_table = families_main.find('table')
families_table_body = families_table.find('tbody')
families_table_rows = families_table_body.find_all('tr')
print('There are', len(families_table_rows), 'families')

problems = []

# for each family get the list of genera
for families_table_row in families_table_rows:
  family_name_td = families_table_row.find('td')
  family_name = family_name_td.find('strong')
  
  print('fetching genera for', family_name.text)
  genera_url_elem = families_table_row.find(title="Genera list")
  genera_url = genera_url_elem['href']
  genera_page = requests.get(urljoin(base_url, genera_url))
  genera_soup = BeautifulSoup(genera_page.content, 'html.parser')
  genera_main = genera_soup.find('main') 
  genera_table = genera_main.find('table')
  genera_table_body = genera_table.find('tbody')
  genera_table_rows = genera_table_body.find_all('tr')

  if len(genera_table_rows) == 1:
    print(family_name.text, 'has 1 genus')
  else:
    print(family_name.text, 'has', len(genera_table_rows), 'genera')

  for genus_row in genera_table_rows:
    
    genus_name_td = genus_row.find('td')
    genus_name = genus_name_td.find('strong').text
    genus_url_elem = genus_row.find(title="Show species entries")
    genus_catalog_url = genus_url_elem['href']
    genus_catalog_page = requests.get(urljoin(base_url, genus_catalog_url))
    genus_catalog_page_soup = BeautifulSoup(genus_catalog_page.content, 'html.parser')
    genus_catalog_page_main = genus_catalog_page_soup.find('main')

    
    
    page_genus_name_elem =  genus_catalog_page_main.find(class_="genusTitle")
    page_genus_name = page_genus_name_elem.find('strong').text
    
    if genus_name != page_genus_name:
      problems.append(genus_name)
      continue
    
    genus_species = []

    # we need to iterate over divs of main only, because we don't want the white space between them
    first_species = genus_catalog_page_main.find('div', class_='speciesTitle')
    first_species_detail = first_species.find_next_sibling('div')

    genus_species.append( {"species": first_species, "details": first_species_detail })

    next_species = first_species_detail.find_next_sibling('div')
    while next_species is not None:
      next_species_detail = next_species.find_next_sibling('div')
      genus_species.append( {"species": next_species, "details": next_species_detail })
      next_species = next_species_detail.find_next_sibling('div')
    




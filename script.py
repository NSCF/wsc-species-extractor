# This is still under construction. The original idea was to try and infer synonyms from the name usages listed under each
# species. But not very easy, there are lots of nuances in the WSC, such as informal names, quoted names, etc. The names are
# listed as they were originally published, without the necessary corrections to be code compliant. The WSC also 
# change the names when species are moved from one genus to another to match the gender, so it's difficult to match things
# up using the synonyms and transfers sections.

# Overall an interesting exercise in scraping a website, to see inconsistencies and glitches, and all sorts of other things. 
# Noteably the pages are designed for scraping, no data attributes, much of the data are outside of tags, etc.

#  Decided just to use the datasets that were sent to me originally, they might not be as comprehensive but hopefully good enough!

from datetime import datetime
import csv, time
from functions import get_family_urls, get_genus_page_urls, get_genus_page_soup, check_genus_page_match, get_species_and_chrysonyms

start = time.perf_counter()

print('fetching family list')
family_urls = get_family_urls('families')
print('got', len(family_urls.keys()), 'families')

# for each family get the list of genera and parse
problems = {}
records = []
# for testing, set to a high number to get all the families
family_limit = 1000
family_count = 0
for family in family_urls:
  print('fetching genera for', family)
  genus_page_urls = get_genus_page_urls(family_urls[family])
  
  genus_count = len(genus_page_urls.keys())
  if genus_count == 1:
    print(family, 'has one genus')
  else:
    print(family, 'has', genus_count, 'genera')

  for genus in genus_page_urls:
    genus_page = get_genus_page_soup(genus_page_urls[genus])
    if check_genus_page_match(genus, genus_page):
      species_and_synonyms = get_species_and_chrysonyms(genus_page)
      valid_names = list(filter(lambda x: x['acceptedNameID'] is None, species_and_synonyms))
      print(genus, 'has', len(valid_names), 'species and', len(species_and_synonyms) - len(valid_names), 'synonyms')
      records += species_and_synonyms
    else:
      if family in problems:
        problems[family].append(genus)
      else:
        problems[family] = [genus]
  
  # just for testing
  family_count += 1
  if family_count == family_limit:
    break

end = time.perf_counter()
elapsed = end - start
hours, remainder = divmod(elapsed, 3600)
minutes, seconds = divmod(remainder, 60)
  
if len(problems.keys()) > 0:
  print('There were problems with the following taxa:')
  for family in problems:
    print(family +':', '|'.join(problems[family]))

total_valid_names = list(filter(lambda x: x['acceptedNameID'] is None, records))
print('Total valid names:', len(total_valid_names))
print('Total synonyms:', len(records) - len(total_valid_names))
print('Total time:', f"{int(hours):02}h{int(minutes):02}m{round(seconds):02}s")
print('writing results file...')
today = datetime.today().isoformat().split('T')[0].replace('-','')
file_name = 'wsc-species-and-synonyms-' + today + '.csv'

with open(file_name, 'w', encoding='utf8', newline='', errors='ignore') as csvfile:
  writer = csv.DictWriter(csvfile, fieldnames=records[0].keys(), )
  writer.writeheader()
  writer.writerows(records)

print('all done!')  

  
    


      
    

    




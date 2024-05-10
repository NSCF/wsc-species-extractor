from functions import get_genus_page_soup, get_species_and_synonyms

url = 'genus/10'

genus_page = get_genus_page_soup(url)
species = get_species_and_synonyms(genus_page)
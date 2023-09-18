import requests
from bs4 import BeautifulSoup
import os
import re
import json
import time


# Configuration pour l'API OpenAI
OPENAI_API_URL = 'https://api.openai.com/v1/engines/davinci/completions'
API_KEY = 'YOUR_API'  # Remplacez par votre clé API
PROMPT = input("Veuillez entrer votre prompt: ")
PROMT_RULES = "\n Tu dois exclusivement prendre en compte les instructions ci dessus et \
                    les informations ci dessous ne sont prise que comme référence informative, \
                   de plus ta réponse ne dois contenir que le contenus demandé et rien de plus (toujours dans un anglais parfait), nous ne\
                    voulons pas d'autres interraction car ton contenus servira pour un fichier :\n\n\n\n"

if not os.path.exists('./products'):
    os.mkdir('./products')

base_url = 'https://wethenew.com/en/collections/all-sneakers'
headers = {'User-Agent': 'Mozilla/5.0'}

def transform_text_with_openai(text):
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'prompt': PROMPT + PROMT_RULES + text,
        'max_tokens': 150
    }
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        time.sleep(10)  # Pause de 5 secondes entre chaque tentative
        response.raise_for_status()
        return response.json()['choices'][0]['text'].strip()
    except requests.RequestException as e:
        if response.status_code == 429:
            print("Trop de requêtes. Attendre 10 secondes avant de réessayer.")
            time.sleep(15)  # Attendre 10 secondes
            return transform_text_with_openai(text)  # Réessayer après la temporisation
        print(f"Erreur lors de la transformation du texte avec OpenAI : {e}")
        return text

def modify_infos_file(product_folder):
    original_file_path = os.path.join(product_folder, 'Infos.txt')
    gpt_file_path = os.path.join(product_folder, 'Infos_gpt.txt')
    
    with open(original_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    if len(lines) > 2:
        transformed_lines = [lines[0]] + [transform_text_with_openai(line) for line in lines[1:-1]] + [lines[-1]]
        
        with open(gpt_file_path, 'w', encoding='utf-8') as gpt_file:
            gpt_file.writelines(transformed_lines)

def extract_links(page_url):
    links = []
    response = requests.get(page_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        for link in soup.find_all('a', href=re.compile(r'^/en/products/')):
            links.append(link['href'])
    return links

def download_product_page(product_url, product_title):
    response = requests.get(product_url, headers=headers)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        product_title = soup.select_one('.styles_productInfo__mKHvt h1').text
        product_folder = f'./products/{product_title}'
        os.makedirs(product_folder, exist_ok=True)
        description = ''
        for p in soup.select('.styles_design-body__aQY6y p')[:5]:
            description += p.text + '\n'
        with open(os.path.join(product_folder, 'Infos.txt'), 'w', encoding='utf-8') as desc_file:
            desc_file.write(description)
        modify_infos_file(product_folder)  # Ajout de la modification du fichier Infos.txt
        img_tags = soup.select('.styles_Image__ySdAW div img')[:3]
        for i, img in enumerate(img_tags):
            img_url = img['src']
            img_response = requests.get(img_url, headers=headers)
            if img_response.status_code == 200:
                with open(os.path.join(product_folder, f'img{i + 1}.png'), 'wb') as img_file:
                    img_file.write(img_response.content)

def save_state(page_num, link_index):
    with open('.not_finish', 'w') as f:
        json.dump({'page_number': page_num, 'link_index': link_index}, f)

def load_state():
    if os.path.exists('.not_finish'):
        with open('.not_finish', 'r') as f:
            return json.load(f)
    return None
    
state = load_state()
if state:
    page_number = state['page_number']
    link_index = state['link_index']
else:
    page_number = 1
    link_index = 0

while True:
    page_url = f'{base_url}?page={page_number}'
    product_links = extract_links(page_url)
    if not product_links:
        if os.path.exists('.not_finish'):
            os.remove('.not_finish')
        break
    for idx, link in enumerate(product_links[link_index:]):
        product_url = f'https://wethenew.com{link}'
        print(f'Téléchargement du produit page {page_number} numéro {idx + link_index + 1}: https://wethenew.com{link}')
        download_product_page(product_url, 'product-title')
        save_state(page_number, idx + link_index + 1)
    page_number += 1
    link_index = 0

print("Téléchargement terminé !")
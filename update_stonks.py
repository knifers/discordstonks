import json
import requests
import datetime
import os

# --- KONFIGURACJA ---
# Tutaj ustalamy, jak liczymy cenę.
# Obecnie: Suma Gwiazdek i Subskrybentów.
def calculate_price(stars, subs):
    # Możesz tu zmienić logikę, np. (stars * 2) + subs
    total_stars = stars if stars else 0
    total_subs = subs if subs else 0
    return total_stars + total_subs

# Nagłówek, żeby Reddit nas nie zablokował (udajemy przeglądarkę)
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def get_github_stars(repo_name):
    if not repo_name: return 0
    try:
        url = f"https://api.github.com/repos/{repo_name}"
        # GitHub Actions daje nam token automatycznie, użyjmy go dla wyższych limitów
        token = os.environ.get('GITHUB_TOKEN')
        auth_header = {'Authorization': f'token {token}'} if token else {}
        
        r = requests.get(url, headers=auth_header)
        if r.status_code == 200:
            return r.json().get('stargazers_count', 0)
    except Exception as e:
        print(f"Błąd GitHub dla {repo_name}: {e}")
    return 0

def get_reddit_subs(subreddit):
    if not subreddit: return 0
    try:
        url = f"https://www.reddit.com/r/{subreddit}/about.json"
        r = requests.get(url, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            return data.get('data', {}).get('subscribers', 0)
    except Exception as e:
        print(f"Błąd Reddit dla {subreddit}: {e}")
    return 0

# --- GŁÓWNA PĘTLA ---
def main():
    # 1. Wczytaj obecną bazę danych
    with open('stonks.json', 'r') as f:
        db = json.load(f)

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Jeśli dzisiejsza data już jest w historii, nie dodawaj jej drugi raz (zabezpieczenie)
    if db['history_dates'][-1] != today:
        db['history_dates'].append(today)
        # Ograniczamy wykres do ostatnich 30 dni, żeby nie spuchł
        if len(db['history_dates']) > 30:
            db['history_dates'].pop(0)

    print(f"Aktualizacja notowań na dzień: {today}")

    # 2. Przelicz każdą aplikację
    for app in db['apps']:
        print(f"Sprawdzam: {app['name']}...")
        
        stars = get_github_stars(app.get('github_repo'))
        subs = get_reddit_subs(app.get('reddit_sub'))
        
        new_price = calculate_price(stars, subs)
        
        # Jeśli API zawiodło i zwróciło 0 (a wcześniej było więcej), użyj starej ceny
        # żeby uniknąć krachu na wykresie przez błąd sieci
        if new_price == 0 and app['current_price'] > 0:
            print(f"⚠️ Ostrzeżenie: Pobrano 0 dla {app['name']}, zachowuję starą cenę.")
            new_price = app['current_price']

        # Oblicz zmianę procentową
        old_price = app['current_price']
        if old_price > 0:
            change = ((new_price - old_price) / old_price) * 100
            app['change_24h'] = round(change, 2)
        else:
            app['change_24h'] = 0.0

        # Aktualizuj dane
        app['current_price'] = new_price
        
        # Dodaj do historii wykresu
        app['history'].append(new_price)
        if len(app['history']) > 30: # Trzymaj tylko 30 ostatnich punktów
            app['history'].pop(0)

        print(f" -> Nowa cena: {new_price} (Stars: {stars}, Subs: {subs})")

    db['updated_at'] = today

    # 3. Zapisz bazę
    with open('stonks.json', 'w') as f:
        json.dump(db, f, indent=2)

if __name__ == "__main__":
    main()

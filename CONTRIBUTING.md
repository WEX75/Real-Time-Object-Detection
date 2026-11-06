# Cum lucrăm pe repo

Regula de bază: **nimeni nu face push direct pe `main`.** `main` e versiunea care merge mereu și pe care o arătăm la demo. Fiecare lucrează pe un branch al lui și o aduce în `main` printr-un pull request (PR), după ce trec testele.

## Ce e un branch, pe scurt

Un branch e o copie paralelă a codului. Lucrezi pe ea cât vrei, faci commit-uri, iar `main` nu se schimbă. Când ai terminat, ceri prin PR ca modificările tale să intre în `main`. Așa doi oameni pot lucra în același timp fără să-și strice codul unul altuia.

## O singură dată, la început

```bash
git clone https://github.com/WEX75/Real-Time-Object-Detection.git
cd Real-Time-Object-Detection
git config user.name "Numele Tău"
git config user.email "emailul-de-pe-github@exemplu.com"
```

Pornește aplicația după [README](README.md) și verifică că merge înainte să schimbi ceva.

## De fiecare dată când începi ceva nou

```bash
git switch main
git pull                                  # aduci ce au făcut ceilalți
git switch -c feature/nume-scurt          # ex: feature/regula-zone-empty
```

Numele branch-ului începe cu `feature/` (sau `fix/` pentru o reparație). CI-ul rulează automat testele pe orice branch `feature/**`.

## Cât lucrezi

```bash
git status                                # ce fișiere ai schimbat
git add backend/app/rules.py backend/tests/test_rules.py
git commit -m "rules: add zone_empty rule"
git push -u origin feature/nume-scurt     # prima dată; după aceea doar: git push
```

- Commit-uri mici, mesaj la imperativ, fără emoji.
- Înainte de push rulează testele (vezi README, secțiunea Tests). Dacă pică local, pică și pe GitHub.
- Nu pune în git: `.venv/`, `node_modules/`, `*.pt`, `*.sqlite3`, fișiere `.env`. Sunt deja în `.gitignore`.

## Când ai terminat: pull request

1. Pe GitHub apare butonul **Compare & pull request** pentru branch-ul tău. Apasă-l.
2. Baza (`base`) e `main`. Scrie în descriere ce ai făcut și cum se testează.
3. Așteaptă bifa verde de la CI (`pytest-backend` și `build-frontend`). Cu X roșu nu se face merge.
4. Un coleg se uită peste cod și aprobă. Apoi **Merge pull request**.
5. Local:

```bash
git switch main
git pull
git branch -d feature/nume-scurt
```

## Dacă `main` s-a schimbat cât ai lucrat tu

```bash
git switch main
git pull
git switch feature/nume-scurt
git merge main
```

Dacă git spune `CONFLICT`, deschide fișierele marcate. Vei vedea:

```
<<<<<<< HEAD
codul tău
=======
codul din main
>>>>>>> main
```

Păstrează varianta corectă (sau o combinație), șterge cele trei linii-marcaj, apoi:

```bash
git add fisierul-reparat
git commit
python -m pytest -m "not model"           # din backend/, cu venv activ
git push
```

Dacă nu știi pe care variantă s-o păstrezi, întreabă-l pe cel care a scris codul din `main`. Nu șterge codul altcuiva doar ca să dispară conflictul.

## Cine ce atinge

Contractul dintre frontend și backend (rutele `/api/...`, mesajele de pe `/ws/detect`) e descris în `CLAUDE.md`, secțiunea 10. Nu îl schimba fără să anunți echipa: frontend-ul și backend-ul se lucrează în paralel și se bazează pe el.

Orice decizie de arhitectură nouă (o bibliotecă nouă, alt mod de stocare, alt protocol) primește un ADR scurt în `docs/`, numerotat după ultimul.

## Greșeli des întâlnite

| Mesaj | Ce înseamnă | Ce faci |
| --- | --- | --- |
| `rejected ... (fetch first)` la push | Cineva a împins înaintea ta pe același branch | `git pull`, rezolvi conflictele, apoi `git push` |
| `Your local changes would be overwritten` | Ai modificări necommise | `git add` + `git commit` (sau `git stash`), apoi repeți comanda |
| `pytest` pe GitHub: `collected 0 items`, exit code 5 | Nu există niciun test | Adaugă teste pentru codul nou |
| `ModuleNotFoundError` în CI | Ai folosit o bibliotecă care nu e în `requirements.txt` | Adaug-o în `requirements.txt` (și anunță echipa) |

# Fantasykollen deploy-checklista

## Miljövariabler

- `SITE_URL`: publik domän, till exempel `https://www.fantasykollen.se`
- `PLAUSIBLE_DOMAIN`: sätt om Plausible används
- `GA_MEASUREMENT_ID`: sätt om Google Analytics används

## Startkommando

```bash
gunicorn app:app
```

## Schemalagd datahämtning

Kör var 15:e minut eller inför deadline:

```bash
python scripts/update_data.py
```

Alternativt med Flask CLI:

```bash
flask --app app refresh-data
```

## Efter deploy

- Lägg till domänen i Google Search Console.
- Skicka in `/sitemap.xml`.
- Kontrollera `/robots.txt`.
- Kontrollera att canonical-URL:er använder rätt domän.
- Aktivera analytics först när integritetspolicyn är uppdaterad.

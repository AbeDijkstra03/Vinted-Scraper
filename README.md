# Vinted Scraper

Originally created for my start-up called MoneyBear, hence the name.

It is largely based on https://github.com/Giglium/vinted_scraper

I never finished the project, because we shifted away from the idea of scraping Vinted using our own tools and we started using the eBay API, but it did work at some point, although it was quite slow.

The tests don't pass and it might be outdated by now because Vinted changes the structure of their website every couple of months.

I used to host it on PythonAnywhere.

scraper.py contains a Flask API, it might be in the wrong folder.

You have to install the vinted_scraper_moneybear first using pip or uv and then import that inside scraper.py 
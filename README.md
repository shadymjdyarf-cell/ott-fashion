# OTT · 옷 — Fashion for Everyone

#### Video Demo: <URL HERE>
#### Description:

## Overview

OTT (pronounced "ot") is the Korean word for "clothes". This project is a
Korean-inspired fashion assistant built with Flask, Python, and SQLite. It
helps people of all backgrounds discover their style, build outfits from
their own wardrobe, explore global fashion trends, and stay inspired - without
judgment, without labels, and without barriers.

## The Core Idea

Fashion is often exclusive. It tells people what they should look like and what
they should avoid. OTT is the opposite: it is inclusive by design. All clothes
live in the same space. There are no filters for skin color, body type,
gender, religion, or disability. The only way to organize items is by occasion
and by style - because clothes are worn for moments, not for labels.

## Features

### Wardrobe
Users can add clothes with photos, choose an occasion (Gym, Sports, School,
Casual, Occasion, Trend, Vintage, Halloween), and tag a style (K-Pop, Old
Money, Street, Minimal, Boho, Classic, Retro, Korean, Vintage). Items can be
marked as "Viral" to highlight trending pieces, and users can find duplicates
in their wardrobe with one click.

### Wishlist
Save things you want to buy or make at home. DIY items include materials,
tools, difficulty level, and steps. Prices are shown in three currencies
(USD, KRW, EGP) with live exchange rates. Users can also track price changes
over time.

### AI Stylist
A rule-based engine picks a complete outfit from the user's own wardrobe
based on occasion, weather, and mood. It explains why it chose each item,
and gives a styling tip.

### Trend Dictionary
A curated list of fashion terms (Y2K, Old Money, Korean Ulzzang, Balletcore,
and more) with descriptions, eras, and color palettes. Users can refresh
trends from Vogue, Hypebeast, Koreaboo, and Soompi RSS feeds.

### Discover
A Pinterest-style inspiration page that fetches Korean fashion photos from
Unsplash with infinite scroll.

### Community
Users can follow each other, like outfits, and comment on shared looks.
A community wall shows the top-rated outfits.

### Camera & Themes
Users pick from 10 themes (80s Retro, Y2K, Halloween, Korean Street, and
more), apply CSS filters to the camera, take a photo, and save it to their
wardrobe.

### Extra Tools
- Weather API (Open-Meteo) for daily styling suggestions
- Korean size converter (US/EU/UK/KR for men and women)
- Trending K-hashtags directory
- Photo editor with 8 filters
- OCR to read brand names from photos (Tesseract.js)
- Barcode scanner (QuaggaJS)
- K-Pop idol match (rule-based)
- Fashion weeks directory
- Style DNA (learns from user preferences)
- Before/After transformation gallery
- Personal calendar for upcoming occasions
- Style journal
- Personal challenges
- Progress tracking
- Achievements and badges

## Multilingual

The interface supports English, Arabic (with RTL layout), and Korean. Users
switch languages from the sidebar and their choice is saved.

## Accessibility

- Dyslexia-friendly font toggle
- Reduce-motion mode
- Read-aloud (text-to-speech)
- Keyboard shortcuts (Ctrl+K for search, Alt+W for wardrobe, and more)
- Focus-visible outlines for keyboard users
- High contrast in dark mode

## Design

The visual theme is inspired by student notebooks: warm paper background,
dashed borders, a handwritten font for headings, and warm orange and green
colors. The goal is to feel friendly and personal, not corporate.

## Tech Stack

- Backend: Flask (Python 3.13)
- Database: SQLite with CS50 SQL
- Frontend: HTML, CSS, Vanilla JavaScript
- Fonts: Caveat, Inter, Noto Sans KR, Noto Sans Arabic
- Images: Unsplash API (Korean fashion collections)
- RSS: Vogue, Hypebeast, Highsnobiety, Koreaboo, Soompi
- Free APIs: Open-Meteo (weather), DiceBear (avatars)
- Libraries: Tesseract.js (OCR), QuaggaJS (barcode)

## Files

- app.py - Flask application with all routes
- helpers.py - Helper functions, AI engine, RSS fetch, exchange rates
- translations.py - English, Arabic, Korean translations
- config.py - API keys and configuration
- schema.sql - Database schema
- templates/ - 30+ HTML pages
- static/css/style.css - The "Student Notebook" theme
- static/js/app.js - Sidebar, dark mode, share, voice search
- static/uploads/ - User uploaded images

## Design Decisions

I chose Flask over Django because it is lighter and easier to customize. I
chose SQLite because CS50 teaches it and it works well for single-server
deployments. I chose the "notebook" theme because fashion should feel personal
and warm, not cold and corporate.

## AI Usage

Claude AI was used as a coding assistant for debugging, structure, and
translation help. All design decisions, feature choices, and the core idea
are my own. No AI-generated images were used - all graphics come from
Unsplash (human photographers), DiceBear (human designers), or were drawn
by hand in SVG.

## Author

- Name: Shady Magdy Abd El-Hafiz
- GitHub: shadymjdyarf-cell
- edX: shadymjdyarf
- City: Alexandria, Egypt

# OTT · 옷 — Fashion Assistant

#### Video Demo: https://youtu.be/Uh6HIIyB5K0
#### Description:

Hello, my name is Shady Magdy Abd El-Hafiz. This is my final project for CS50x, and it is called OTT (pronounced "oat"), which is the Korean word (옷) for "clothes". I want to tell you the story from the beginning, because this project is not just code; it is something I lived and learned a lot from.

**The Core Idea:**
Imagine waking up in the morning with an important errand, standing in front of your closet or scrolling through an app, asking yourself: "What should I wear today?" and "What should I go buy tomorrow?" I always struggled with these two moments. That is why I built OTT to solve exactly these problems. The app lets you browse for inspiration, and then asks the AI Stylist (built on my own rules) to pick a full outfit from the clothes you already own. If you need something new, you add it to the Wishlist to go look for it tomorrow.

**Seasonal Themes:**
Another feature I am very proud of is that the site "breathes" with time. The website automatically changes its theme depending on the season. For example, in October, you will find the site changed to a "Halloween" theme (orange and pumpkins), in December it turns into a "Christmas" theme (red and green), and during Ramadan, you will find a special golden touch. The idea is that fashion and clothing are tied to the weather and occasions, so I wanted the site to feel alive and expressive of the current month.

**Core Features:**
*   **Smart Wardrobe:** Add clothes with photos, categorized by 8 occasions (Gym, Casual, Vintage, etc.) and 9 styles (K-Pop, Old Money, etc.). It includes a "Viral" feature to mark trending items, a "Find Duplicates" feature, and a global search.
*   **Wishlist:** For items you want to buy or make at home (DIY). You can log materials, tools, difficulty level, with automatic currency conversion (USD, KRW, EGP) and price history tracking.
*   **AI Stylist:** Picks a complete outfit from your clothes (Top, Bottom, Shoes) based on the occasion, weather, and mood, and explains "why" it chose each piece. This is a rule-based engine written entirely by me, not relying on any external service, and it works offline.
*   **Trends:** A dictionary of fashion terms (like Y2K, Old Money), auto-updated from RSS feeds like Vogue. Each trend has a detail page with its color palette and styling tips.
*   **Camera & Themes:** 10 themes (like Halloween, Y2K, Korean Street) that apply a live filter to your camera.
*   **Style DNA & Tools:** A "Style DNA" page that learns your preferences, a "K-Idol Match" tool, a photo editor (8 filters), an OCR reader using Tesseract.js, a barcode scanner using QuaggaJS, a weather widget, and a Korean size converter.
*   **Languages, Design & Accessibility:** 3 languages (English, Arabic RTL, Korean), a warm "Student Notebook" theme, 6 color themes, dark mode, a dyslexia-friendly font, read-aloud text-to-speech, and a PWA that works offline.
*   **Community:** Allows posting photos, stories, basic interactions, and comments. *(With apologies for any incomplete details, as explained above)*.

**The Struggle:**
I want to be honest with you; this project was very hard. In the first week, the session database broke on me, and it took me 3 days to understand that Flask needs specific configurations. After that, while trying to build the wardrobe, I accidentally deleted the database twice and lost all my test items, so I had to learn to write everything in schema.sql from scratch. The hardest part was the AI Stylist; the first version picked a winter jacket in the middle of summer, and I had to rewrite the color logic 3 times. Later, while adding languages, I discovered Arabic needs RTL, and that English was hardcoded inside every page, so I had to edit 30 HTML templates. The whole project took about two months, and I deleted half the code I wrote and started over more than once.

**The Confession:**
And here, I must confess something. I reached very high results in the app and put massive effort into it, but because of **my perfectionism**, I was losing the site more than once. Every time I tried to add a new feature, I got scared, rewrote entire sections, and sometimes broke what was working. In the end, I decided that this is enough, and what I have is very good. **I must sincerely apologize for issues in the Community section.** Because of my perfectionism, I could not deliver it in the full form it initially had, which would have given me a complete product. I am very sorry for anyone who notices this. **CS50 deserves better than this, and I know I could have given more, but perfectionism got the best of me.**

**Design Decisions:**
*   **Why Flask?** I chose it because it is lightweight and easy, allowing me to build the site piece by piece without feeling the framework was fighting me.
*   **Why SQLite?** Because CS50 teaches it, and it is more than enough for the project.
*   **Why this theme?** I chose the "Student Notebook" theme because I personally love paper and notes, and I felt fashion needs something warm, not cold like luxury apps. That's why I used handwritten fonts, notebook-style lines, and calm colors.
*   **Why a local AI?** Because I did not want the app to stop if the internet cuts out, so I built it with a rule-based engine that works offline.

**Technologies:**
Flask (Python), SQLite, HTML, CSS, JavaScript. With free services (Unsplash for images, Open-Meteo for weather).

**AI Usage:**
I used Claude (AI) as a coding assistant for debugging, some design suggestions, and code structure. However, all project logic, the idea, feature choices, and design are entirely my own. **No AI-generated images were used**; all images are from human photographers (Unsplash) or SVG drawings.

**Author:**
*   Name: Shady Magdy Abd El-Hafiz
*   GitHub: shadymjdyarf-cell
*   edX: shadymjdyarf
*   City: Alexandria, Egypt

from flask import Flask, request, render_template_string
import pandas as pd
import re

app = Flask(__name__)
df = pd.read_csv("brands_data.csv", encoding="ISO-8859-1")

def highlight_keywords(text, keywords):
    for kw in keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        text = pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    keyword = request.form.get("keyword", "").strip().lower()
    selected_brand = request.form.get("brand", "All")
    selected_year = request.form.get("year", "All")
    selected_country = request.form.get("country", "All")

    # Initial filtering based on keyword
    filtered_df = df.copy()
    if keyword:
        keywords = keyword.split()
        # Step 1: Full phrase
        filtered_df = df[df['product_description'].astype(str).str.lower().str.contains(keyword)]
        # Step 2: All words
        if filtered_df.empty and len(keywords) > 1:
            filtered_df = df[df['product_description'].astype(str).apply(
                lambda desc: all(kw in desc.lower() for kw in keywords))]

    else:
        keywords = []

    # Apply hierarchy to filters
    hierarchy_df = filtered_df.copy()
    if selected_brand != "All":
        hierarchy_df = hierarchy_df[hierarchy_df['brand_name'] == selected_brand]
    if selected_year != "All":
        hierarchy_df = hierarchy_df[hierarchy_df['created_year'].astype(str) == selected_year]
    if selected_country != "All":
        hierarchy_df = hierarchy_df[hierarchy_df['country'] == selected_country]

    # Update filters based on current hierarchy
    brands = sorted(filtered_df['brand_name'].dropna().unique().tolist())
    years = sorted(filtered_df[filtered_df['brand_name'] == selected_brand]['created_year'].dropna().astype(str).unique().tolist()) if selected_brand != "All" else []
    if selected_year != "All":
        countries = sorted(filtered_df[(filtered_df['brand_name'] == selected_brand) &
                                       (filtered_df['created_year'].astype(str) == selected_year)]['country'].dropna().unique().tolist())
    elif selected_brand != "All":
        countries = sorted(filtered_df[filtered_df['brand_name'] == selected_brand]['country'].dropna().unique().tolist())
    else:
        countries = sorted(filtered_df['country'].dropna().unique().tolist())

    # Final product list
    products = hierarchy_df.to_dict(orient="records")

    for p in products:
        desc = str(p.get('product_description') or "")
        if keyword:
            p['short_description'] = highlight_keywords(desc[:200], keywords)
            p['full_description'] = highlight_keywords(desc, keywords)
        else:
            p['short_description'] = desc[:200]
            p['full_description'] = desc

    return render_template_string(TEMPLATE, 
                                  products=products,
                                  brands=brands,
                                  years=years,
                                  countries=countries,
                                  selected_brand=selected_brand,
                                  selected_year=selected_year,
                                  selected_country=selected_country,
                                  keyword=keyword,
                                  total=len(products))

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>D&J Product Search</title>
    <style>
        body { font-family: Arial; background: #f7f7f7; padding: 20px; }
        input, select, button { padding: 8px; margin: 5px; }
        .slider { display: flex; overflow-x: auto; scroll-snap-type: x mandatory; }
        .card {
            flex: 0 0 600px; display: flex; scroll-snap-align: start;
            background: #fff; border-radius: 10px; overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1); margin-right: 20px;
        }
        .card .image { width: 50%; }
        .card .image img { width: 100%; height: 100%; object-fit: cover; }
        .card .info { width: 50%; padding: 15px; font-size: 14px; position: relative; }
        .card .info h3 { margin: 0 0 10px 0; font-size: 18px; }
        .plus-btn {
            position: absolute; bottom: 10px; right: 15px; background: #007bff; color: white; border: none;
            border-radius: 50%; width: 25px; height: 25px; font-weight: bold; cursor: pointer;
        }
        mark { background: yellow; }
        .modal {
            display: none; position: fixed; z-index: 1000; padding-top: 100px;
            left: 0; top: 0; width: 100%; height: 100%;
            background-color: rgba(0,0,0,0.6);
        }
        .modal-content {
            background-color: #fff; margin: auto; padding: 20px;
            border-radius: 10px; width: 60%;
        }
        .close {
            color: #aaa; float: right; font-size: 28px;
            font-weight: bold; cursor: pointer;
        }
    </style>
</head>
<body>

<h1>D&J Product Explorer</h1>
<form method="POST">
    <input type="text" name="keyword" placeholder="Search..." value="{{ keyword }}">
    <select name="brand">
        <option value="All">All Brands</option>
        {% for b in brands %}
        <option value="{{ b }}" {% if b == selected_brand %}selected{% endif %}>{{ b }}</option>
        {% endfor %}
    </select>
    <select name="year">
        <option value="All">All Years</option>
        {% for y in years %}
        <option value="{{ y }}" {% if y == selected_year %}selected{% endif %}>{{ y }}</option>
        {% endfor %}
    </select>
    <select name="country">
        <option value="All">All Countries</option>
        {% for c in countries %}
        <option value="{{ c }}" {% if c == selected_country %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
    </select>
    <button type="submit">Search</button>
</form>

<p><strong>{{ total }} product{{ 's' if total != 1 else '' }} found</strong></p>

<div class="slider">
    {% for p in products %}
    <div class="card">
        <div class="image">
            <img src="{{ p['product_image_aws'] or p['product_image'] }}">
        </div>
        <div class="info">
            <h3>{{ p['product_name'] }}</h3>
            <p><b>Brand:</b> {{ p['brand_name'] }}</p>
            <p><b>Category:</b> {{ p['product_category'] }}</p>
            <p><b>Price:</b> ${{ p['price_usd'] }}</p>
            <p>{{ p['short_description'] }} <button class="plus-btn" onclick="showModal({{ loop.index0 }})">+</button></p>
        </div>
    </div>
    {% endfor %}
</div>

{% for p in products %}
<div id="modal{{ loop.index0 }}" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeModal({{ loop.index0 }})">&times;</span>
        <h3>{{ p['product_name'] }}</h3>
        <p>{{ p['full_description']|safe }}</p>
    </div>
</div>
{% endfor %}

<script>
function showModal(i) {
    document.getElementById('modal' + i).style.display = 'block';
}
function closeModal(i) {
    document.getElementById('modal' + i).style.display = 'none';
}
window.onclick = function(event) {
    for (let m of document.getElementsByClassName("modal")) {
        if (event.target == m) m.style.display = "none";
    }
}
</script>

</body>
</html>
"""

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)


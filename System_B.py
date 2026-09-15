import pandas as pd
import altair as alt
import re
import itertools


#it kept lagging
alt.data_transformers.disable_max_rows()

CSV = "HarryPotter_dataset.csv"
HTML_link = "System_B.html"

# load and  lean again just in case
allPairingOptions = "All Pairings"

allGenreOptions = "All Genres"

df = pd.read_csv(CSV)
#print("total rows loaded ->", len(df))

#need to convert published to day(it showing at str)
df["published"] = pd.to_datetime(df["published"], errors="coerce")

#remove rows with missing values.
#also did earlier but it's just in case
df = df.dropna(subset=["published", "pairing"]).copy()



# split genre string into separate genre
def get_genres(text):
    # if missing, return empty list
    if pd.isna(text):
        return []

    #remove extra stuff
    parts = re.split(r"[/,;|]", str(text))
    return [p.strip() for p in parts if p.strip()]



# helper to build a clean searchable string for Altair filtering
def norm_genres(text):
    genres = get_genres(text)

    #if missing, return empty list
    if not genres:
        return ""

    # adding | around each genre so altiar can match exact genre names
    return "|" + "|".join(genres) + "|"

# make a new col in df that stores the normalized searchable genre string
df["genre_match"] = df["genre"].apply(norm_genres)




# global controls
#showing only top 20 pairings for drop down cause it was lagging
top_pairings = df["pairing"].value_counts().head(20).index.tolist()
pairing_option = [allPairingOptions] + sorted(top_pairings)

#dropdown pairing + param
pairing_dropdown = alt.binding_select(
    options=pairing_option, 
    name="Pairing: ")
pairing_select = alt.param(
    bind=pairing_dropdown, 
    value=allPairingOptions)

#genre
genre_options = sorted(set(
    itertools.chain.from_iterable(
        df["genre"].dropna().apply(get_genres))))
# add "All Genres" at top
genre_select = [allGenreOptions] + genre_options

#dropdown grene + param
genre_dropdown = alt.binding_select(
    options=genre_select,
    name="Genre: ")
genre_select = alt.param(
    name="genre_select",
    bind=genre_dropdown,
    value=allGenreOptions)

# reusable filter expression for genre
genre_reuseable = (
    f"(genre_select === '{allGenreOptions}') || "
    f"(indexof(datum.genre_match, '|' + genre_select + '|') >= 0)")





# brushing on the time axis in View B
# use pub_month so other views can filter by the same month field
time_brush = alt.selection_interval(encodings=["x"],
                                    mark=alt.BrushConfig(
                                        fill = "lightgray", 
                                        fillOpacity=0,
                                        stroke="gray"))

# lets task 4 filter for pairing
#putting it here so view a + b can also use
draco_pair_select = alt.selection_point(fields=["pairing"], empty=True)


# view b task 3
viewB_df = df.copy()

#convert pub into months in pd
viewB_df["pub_month"] = viewB_df["published"].dt.to_period("M").dt.to_timestamp()

#coount pairing and month
# monthly_counts = (
#     viewB_df.groupby(["pairing", "pub_month"])
#     .size()
#     .reset_index(name="story_count"))

base_B = (
    alt.Chart(viewB_df)
    .transform_filter((pairing_select == allPairingOptions) | 
                      (alt.datum.pairing == pairing_select))
    .transform_filter(genre_reuseable)
    .transform_filter(draco_pair_select)
    .transform_aggregate(story_count="count()",
                         groupby=["pairing","pub_month"]))

#line part
line_B = base_B.mark_line(color="green").encode(
    x=alt.X("pub_month:T", 
            title="Pub yyyy/mm", 
            axis=alt.Axis(format="%b %Y")),
    y=alt.Y("story_count:Q", 
            title="Num of Stories"))

#points
points_B = base_B.mark_point(size=50, 
                             filled=True, 
                             color="purple").encode(
    x=alt.X("pub_month:T", 
            title="Pub yyyy/mm", 
            axis=alt.Axis(format="%b %Y")),
    y=alt.Y("story_count:Q"),

    #for when user hovers over the point. what it'll show
    tooltip=[
        alt.Tooltip("pairing:N", title="Pairing"),
        alt.Tooltip("pub_month:T", title="Published", format="%b %Y"),
        alt.Tooltip("story_count:Q", title="Story count")])

#combining line and the points
view_B = (line_B + points_B).add_params(time_brush).properties(
    title="View B: Story Count Over Time",
    width=900,
    height=500)



#for view A (task 1) pop vs story length -- scatterplot
#make a new datafram
#task 1 needs words, reviews, dav, follows, published, parings
#3 charts side by sode 
viewA_df = df.dropna(
    subset=["words", 
            "reviews", 
            "favs", 
            "follows", 
            "published", 
            "pairing"]).copy()


# make month column so the time brush from View B can filter this view too
viewA_df["pub_month"] = viewA_df["published"].dt.to_period("M").dt.to_timestamp()

#start at 20k words sincce it's been cleaned to remove already 
viewA_df = viewA_df[viewA_df["words"] >= 20000].copy()

base_A = (
    alt.Chart(viewA_df)
    .transform_filter((pairing_select == allPairingOptions) | 
                      (alt.datum.pairing == pairing_select))
    .transform_filter(genre_reuseable)
    .transform_filter(draco_pair_select)
    .transform_filter(time_brush))

#adding b/s it's still starting before 20k words
#b/c altair still pushes for a "nice"
x_words = alt.X(
    "words:Q",
    title="Words",
    scale=alt.Scale(domainMin=20000, nice=False, zero=False))


#helper to not repeat sctter
def make_scatter(y_col, y_title):
    return base_A.mark_circle(size=30, opacity=0.30, clip=True).encode(
        x=x_words,
        y=alt.Y(f"{y_col}:Q", title=y_title),
        tooltip=[
            alt.Tooltip("pairing:N", title="Pairing"),
            alt.Tooltip("words:Q", title="Words"),
            alt.Tooltip(f"{y_col}:Q", title=y_title),
            alt.Tooltip("pub_month:T", title="Pub month", format="%b %Y")]
    ).properties(
        title=f"Words vs {y_title}",
        width=900,
        height=250)

scatter_reviews = make_scatter("reviews", "Reviews")
scatter_favs = make_scatter("favs", "Favs")
scatter_follows = make_scatter("follows", "Follows")

#combine the 3
view_A = alt.vconcat(
    scatter_reviews,
    scatter_favs,
    scatter_follows).properties(
    title="View A: Popularity vs Story Length")



#view c for task 2 and 4
#ranked charts
# left for task 2 and right for task 4

#helper to clean the characters column 
def extract_characters(text):
    if pd.isna(text):
        return []
    #remove all the [ ]
    text = str(text).replace("[", "").replace("]", "")

    #reformatting because it wasnt showing right
    #then make sure it doesnt dup.
    return list(dict.fromkeys(re.findall(r'[A-Z][a-z]+\s(?:[A-Z]\.\s?)+', text)))

#helper, take 
def extract_pairings(text):
    if pd.isna(text):
        return []
    return re.findall(r"\[[^\]]+\]", str(text))




# task 2 data-- character co-occurrence
#need new df again
co_rows = []

for index, row in df.dropna(subset=["characters", "published"]).iterrows():
    chars = extract_characters(row["characters"])
    
    #removing some since theres so many
    if len(chars) < 2:
        continue



# for all possible ordered pairs, add each pair to new list
    for center_char, other_char in itertools.permutations(chars, 2):
        co_rows.append({
            "center_character": center_char,
            "other_character": other_char,
            "published": row["published"],
            "genre_match" : row["genre_match"]})

#make into DF for task 2 
co_occurrence_df = pd.DataFrame(co_rows)

#dropdown options from avail characters.
character_options = sorted(
    co_occurrence_df["center_character"].dropna().unique().tolist())

#dropdown for selected charact in task 2
character_dropdown = alt.binding_select(
    options=character_options, name="Character: ")

#set draco as default
character_select = alt.param(
    name = "character_select",
    bind=character_dropdown, 
    value="Draco M.")

chart_C_left = (
    alt.Chart(co_occurrence_df)
    #.transform_filter(time_brush)
    .transform_filter(alt.datum.center_character == character_select)
    .transform_filter(genre_reuseable)
    .transform_aggregate(
        story_count="count()",
        groupby=["center_character", "other_character"])
    
    #rank high to low
    .transform_window(
        rank="rank(story_count)",
        sort=[alt.SortField("story_count", order="descending")])
    
    #keep only top 10 co occur characters
    .transform_filter(alt.datum.rank <= 10)
    .mark_bar(color="blue")
    .encode(
        y=alt.Y("other_character:N", 
                sort="-x", 
                title="Co-occurring character"),
        x=alt.X("story_count:Q", 
                title="Stories together"),
        tooltip=[
            alt.Tooltip("center_character:N", title="Selected character"),
            alt.Tooltip("other_character:N", title="Other character"),
            alt.Tooltip("story_count:Q", title="Stories together")])
    .properties(
        title="Task 2: Top Co-occurring Characters",
        width=420,
        height=300))

# task 4 data -- top 3 draco pairings in romance genres
draco_pair_rows = []

for index, row in df.dropna(subset=["genre", "pairing", "published"]).iterrows():
    for pair in extract_pairings(row["pairing"]):
        draco_pair_rows.append({
                "pairing": pair,
                "published": row["published"],
                "genre_match": row["genre_match"]})

#make list into df for the chart 
draco_pair_df = pd.DataFrame(draco_pair_rows)

#for view c, right side for task 
chart_C_right = (
    alt.Chart(draco_pair_df)

    #only show pairings that contain that selected character
    .transform_filter("indexof(datum.pairing,character_select)>=0")
    .transform_filter(genre_reuseable)

    #so tooltip can show which charc is selected
    .transform_calculate(selected_character="character_select")

    #repeat for genre
    .transform_calculate(selected_genre="genre_select")
    .transform_aggregate(
        story_count="count()",
        groupby=["pairing",
                 "selected_character",
                 "selected_genre"])
    .transform_window(
        rank="rank(story_count)",
        sort=[alt.SortField("story_count", 
                            order="descending")])
    
    #only top 3
    .transform_filter(alt.datum.rank <= 3)
    .mark_bar(color= "orange")
    .encode(
        y=alt.Y("pairing:N", 
                sort="-x", 
                title="Pairing"),
        x=alt.X("story_count:Q", 
                title="Number of stories"),
        tooltip=[
            alt.Tooltip("selected_character:N", title="Selected Character"),
            alt.Tooltip("selected_genre:N", title="Genre"),
            alt.Tooltip("pairing:N", title="Pairing"),
            alt.Tooltip("story_count:Q", title="Story count")])
    .add_params(draco_pair_select)
    .properties(
        title="Task 4: Top 3 Pairings",
        width=420,
        height=300))





#combine right and left side for view c
view_C = alt.hconcat(
    chart_C_left,
    chart_C_right,
    spacing=30
    ).add_params(
        character_select
        ).resolve_scale(y="independent").properties(
    title="View C: Ranked Relationship Charts")






#putting all views together 
fin_chart = alt.vconcat(
    view_A,
    view_B,
    view_C,
    spacing=20).add_params(
                            pairing_select,
                            genre_select).resolve_scale(
                                            x="independent",
                                            y="independent")

fin_chart.save(HTML_link, embed_options={"actions": False})


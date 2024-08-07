import streamlit as st
import pandas as pd
import numpy as np
import regex
import re
import emoji
from collections import Counter
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

# Define helper functions (same as before)
def preprocess(data):
    pattern = '\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s-\s'

    messages = re.split(pattern, data)[1:]
    dates = re.findall(pattern, data)

    df = pd.DataFrame({'user_message': messages, 'message_date': dates})
    # convert message_date type
    df['message_date'] = pd.to_datetime(df['message_date'], format='%d/%m/%Y, %H:%M - ')

    df.rename(columns={'message_date': 'date'}, inplace=True)

    users = []
    messages = []
    for message in df['user_message']:
        entry = re.split('([\w\W]+?):\s', message)
        if entry[1:]:  # user name
            users.append(entry[1])
            messages.append(" ".join(entry[2:]))
        else:
            users.append('group_notification')
            messages.append(entry[0])

    df['user'] = users
    df['message'] = messages
    df.drop(columns=['user_message'], inplace=True)

    df['only_date'] = df['date'].dt.date
    df['year'] = df['date'].dt.year
    df['month_num'] = df['date'].dt.month
    df['month'] = df['date'].dt.month_name()
    df['day'] = df['date'].dt.day
    df['day_name'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['minute'] = df['date'].dt.minute

    period = []
    for hour in df[['day_name', 'hour']]['hour']:
        if hour == 23:
            period.append(str(hour) + "-" + str('00'))
        elif hour == 0:
            period.append(str('00') + "-" + str(hour + 1))
        else:
            period.append(str(hour) + "-" + str(hour + 1))

    df['period'] = period

    return df

def startsWithDateAndTime(s):
    pattern = r'^\d{1,2}/\d{1,2}/\d{2,4}, \d{1,2}:\d{2}\u202f[apm]{2} -'
    return bool(re.match(pattern, s))

def getDataPoint(line):
    splitLine = line.split(' - ', 1)
    if len(splitLine) < 2:
        return None, None, None, line

    dateTime = splitLine[0]
    message_part = splitLine[1]

    try:
        date, time = dateTime.split(', ')
    except ValueError:
        return None, None, None, message_part

    if ': ' in message_part:
        author, message = message_part.split(': ', 1)
    else:
        author = None
        message = message_part

    # Ensure stripping only if variables are not None
    date = date.strip() if date else None
    time = time.strip() if time else None
    author = author.strip() if author else None
    message = message.strip() if message else None

    return date, time, author, message


def split_count(text):
    emoji_list = []
    data = regex.findall(r'\X', text)
    for word in data:
        if any(emoji.is_emoji(char) for char in word):
            emoji_list.append(word)
    return emoji_list

# Streamlit UI
st.title("WhatsApp Chat Analysis")
uploaded_file = st.file_uploader("Upload your chat file", type=['txt'])

if uploaded_file is not None:
    content = uploaded_file.read().decode('utf-8')

    data = []
    messageBuffer = []
    date, time, author = None, None, None
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if startsWithDateAndTime(line):
            if messageBuffer:
                data.append([date, time, author, ' '.join(messageBuffer)])
            messageBuffer.clear()
            date, time, author, message = getDataPoint(line)
            messageBuffer.append(message)
        else:
            messageBuffer.append(line)
    if messageBuffer:
        data.append([date, time, author, ' '.join(messageBuffer)])

    df = pd.DataFrame(data, columns=['Date', 'Time', 'Author', 'Message'])
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.dropna(subset=['Author'])
    
    st.write(df.head())

    total_messages = df.shape[0]
    media_messages = df[df['Message'] == '<Media omitted>'].shape[0]
    df["emoji"] = df["Message"].apply(split_count)
    emojis = sum(df['emoji'].str.len())
    URLPATTERN = r'(https?://\S+)'
    df['urlcount'] = df.Message.apply(lambda x: re.findall(URLPATTERN, x)).str.len()
    links = np.sum(df.urlcount)

    st.write(f"Total Messages: {total_messages}")
    st.write(f"Media Messages: {media_messages}")
    st.write(f"Total Emojis: {emojis}")
    st.write(f"Total Links: {links}")

    # Additional Analysis and Word Cloud
    text = " ".join(review for review in df['Message'])
    additional_stopwords = {"joined", "using", "bro", "will", "hai", "group", "bhai", "pm", "invite", "link", "<Media omitted>", "Media", "omitted", "message", "kya", "deleted"}
    stopwords = set(STOPWORDS).union(additional_stopwords)
    
    wordcloud = WordCloud(stopwords=stopwords, background_color="white").generate(text)

    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    st.pyplot(plt)

    authors = df['Author'].unique()
    for author in authors:
        req_df = df[df["Author"] == author]
        st.write(f'Statistics of {author} -')
        st.write('Messages Sent:', req_df.shape[0])
        media = df[(df['Message'] == '<Media omitted>') & (df['Author'] == author)].shape[0]
        st.write('Media Messages Sent:', media)
        emojis = sum(req_df['emoji'].str.len())
        st.write('Emojis Sent:', emojis)
        links = sum(req_df["urlcount"])
        st.write('Links Sent:', links)
        st.write()


# # C:\Users\rakesh\.streamlit


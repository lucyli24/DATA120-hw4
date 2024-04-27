import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import csv

def web_scrap(base_url, lvl, target_keyword):
    response = requests.get(base_url)
    response.raise_for_status()  # Check for HTTP errors
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        url_dict = {}
        links = soup.find("ul", class_ = lvl, id = target_keyword)

        if links:
            for link in links.find_all('li'):
                text = link.text.strip()
                a_tag =link.find('a')
                if a_tag:
                    url_link = a_tag.get('href')
                else:
                    url_link = '#'
                url_dict[text] = url_link 
        return url_dict
    
    print("Cannot acess to the HTML content.")

base_url = "http://collegecatalog.uchicago.edu/"
lvl = "nav levelone"
target_keyword = "/thecollege/"
main = web_scrap(base_url, lvl, target_keyword)

# Scraping The Curriculum
curricumlum = base_url + main['The Curriculum'][1:]
core = web_scrap(curricumlum, "nav leveltwo", main["The Curriculum"])
# Scraping Program of Study
pro_of_study = base_url + main['Programs of Study'][1:]
majors = web_scrap(pro_of_study, "nav leveltwo", main["The Curriculum"])
# Merge and filter dictionaries using modern Python techniques
core_keys = [key for i, key in enumerate(core.keys()) if i in range(2, 5) or i >= 6]
all_courses = {k: v for k, v in {**core, **majors}.items() if k in core_keys + list(majors.keys())}

def fetch_course_data(url):
    for i in range(6):
        try:
            response = requests.get(url)
            break
        except ConnectionError:
            time.sleep(6)
            print("Trying again", url)
            response = requests.get(url)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        main_content = soup.find("div", id="content", role="main")
        if main_content:
            # Process main and subsequence course blocks
            main_course_blocks = main_content.find_all("div", class_="courseblock main")
            sub_course_blocks = main_content.find_all("div", class_="courseblock subsequence")
            course_details = get_data(main_course_blocks + sub_course_blocks)
            return course_details
    else:
        print("Failed to get sub webpage:", response.status_code)
        return []

def get_data_info(course_blocks, course_details):
    for block in course_blocks:
        title_element = block.find("p", class_="courseblocktitle")
        if title_element:
            course_number = title_element.text.strip()[:10]
            # Check for duplicate course numbers
            if course_number in course_details['course_nums']:
                continue
            course_details['course_nums'].add(course_number)
            desc_element = block.find("p", class_="courseblockdesc")
            description = desc_element.text.strip() if desc_element else "No description"
            course_details['descs'].append(description)

            details_element = block.find("p", class_="courseblockdetail")
            if details_element:
                details_text = details_element.text.strip()
                course_details['terms'].append(extract_detail(details_text, "Terms Offered:"))
                course_details['equiv'].append(extract_detail(details_text, "Equivalent Course(s):"))
                course_details['prereqs'].append(extract_detail(details_text, "Prerequisite(s):"))
                course_details['inst'].append(extract_detail(details_text, "Instructor(s):"))
            else:
                course_details['terms'].append("None")
                course_details['equiv'].append("None")
                course_details['prereqs'].append("None")
                course_details['inst'].append("None")

def extract_detail(details_text, detail_type):
    start_idx = details_text.find(detail_type)
    if start_idx == -1:
        return "None"
    start_idx += len(detail_type)
    end_idx = details_text.find('|', start_idx)
    detail = details_text[start_idx:end_idx] if end_idx != -1 else details_text[start_idx:]
    return detail.strip().replace(",", ", ").replace("\n", ", ")


def get_course(url_suffix, course_details):
    base_url = "http://collegecatalog.uchicago.edu"
    full_url = base_url + url_suffix
    attempt = 0
    max_attempts = 6

    while attempt < max_attempts:
        try:
            response = requests.get(full_url)
            if response.status_code == 200:
                break
            else:
                print(f"Server responded with status code: {response.status_code}. Retrying...")
        except requests.ConnectionError:
            print(f"Connection failed. Retrying attempt {attempt+1}/{max_attempts}...")
        time.sleep(10)
        attempt += 1

    if attempt == max_attempts:
        print("Failed to retrieve data after several attempts.")
        return

    # Process the successful response
    soup = BeautifulSoup(response.text, 'html.parser')
    main_content = soup.find("div", id="content", role="main")
    if main_content:
        course_blocks = main_content.find_all("div", class_="courseblock")
        if course_blocks:
            get_data_info(course_blocks, course_details)
        else:
            print("No course blocks found at:", full_url)
    else:
        print("Main content not found on the page.")

course_details = {
    'course_nums': set(),
    'descs': [],
    'terms': [],
    'equiv': [],
    'prereqs': [],
    'inst': []
}




for course_name, url_suffix in all_courses.items():
    print(f"Getting data for: {course_name}")
    get_course(url_suffix, course_details)

df = pd.DataFrame({
    'Course Number': list(course_details['course_nums']),
    'Description': course_details['descs'],
    'Terms Offered': course_details['terms'],
    'Equivalent Courses': course_details['equiv'],
    'Prerequisites': course_details['prereqs'],
    'Instructors': course_details['inst']
})

df.to_csv('catalog.csv', index=False)
print("catalog.csv created")


df['Department Code'] = df['Course Number'].str[:4]
department_summary = df['Department Code'].value_counts().reset_index()
department_summary.columns = ['Department Code', 'Total Number of Courses']
department_summary.to_csv('department123.csv', index=False)
print("Department summary saved to 'department.csv'.")

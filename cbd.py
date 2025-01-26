# Use canvasapi to obtain information from college classes
import os #to create directories to save course material
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist #to raise and intercept errors from file not existing
from canvasapi.exceptions import Forbidden #to catch when we cannot access files of the course directly
from bs4 import BeautifulSoup #to parse HTML into a python-readable format
import yaml #for conveniently importing credentials

# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# FUNCTION DEFINITIONS ------------------------------------------------------------------------
def make_valid_folder_name(input_name, is_file = False):
    """
    inputs:
        - input_name (str): name of original object (whether it is a folder, file, etc.)
        - is_file: boolean, True if this is a filename
    returns:
        - str object, valid name for a folder
    """
    output = input_name
    # If the input name is longer than 120 characters, this may cause the system to flag it as too long
    # of a filename. Truncate this.
    if len(input_name) > 120:
        output = output[:120]

    # Create a translation table between the characters that make a folder name invalid to
    # what we would like to replace them with.
    rep = {ord('\\'): '_', ord('/'): '_', ord(':'): '_', ord('*'): '_', ord('?'): '_',
           ord('"'): '_', ord('<'): '_', ord('>'): '_', ord('|'): '_'}

    # Use translate to map out all invalid strings. Strip whitespaces as well.
    output = output.translate(rep).strip()

    # If we are dealing with a folder, remove any trailing periods
    if not is_file:
        # First check if there is a single trailing period;
        if output[-1] == '.':

            # If there are two consecutive periods, split on the double periods and take the 
            # first string in split.
            if output[-2:] == '..':
                output = output.split('..')[0]

            # If this is not the case, that means that there is only one period at the end 
            # of the string. Just remove that period!
            else:
                output = output[:-1]
        

    return output

def download_file(file, dir, urls):
    """
    Download the given file to the selected directory. Also ensures that the file has
        not been downloaded yet.

    Parameters:
        - file: File object, file to be downloaded
        - dir: Directory to be downloaded in
        - urls: set of file urls that have already been downloaded.

    Returns:
        - None, downloads file into specified directory
    """
    # First check to see if the file has already been downloaded; if not, we proceed to download.
    file_url = file.url

    if file_url in urls:
        return
    
    # Also check to see if the file is a valid_filetype (i.e. it is not a video)
    if not valid_filetype(file):
        return
    
    # We must first check to see if the passed-in directory exists; if not, create it!
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    # Create a path to save the file in.
    file_path = f"{dir}/{make_valid_folder_name(file.display_name, is_file = True)}"

    # Check to see if the file already exists; if not, we can attempt to downlaod the file.
    # If the file doesn't download, we can print the file's name, associated error, and continue.
    if not os.path.exists(file_path):
        try:
            file.download(file_path)
            urls.add(file_url)

        except ResourceDoesNotExist:
            print(f'The file {file.display_name} could not be downloaded.')
            print(f'The associated resource does not exist.')

        except MemoryError:
            print(f'The file {file.display_name} could not be downloaded.')
            print(f'The file was either too large to download, or your system does not have enough space.')
        
        except:
            print(f'The file {file.display_name} could not be downloaded.')

    return

def download_files_from_html(loose_html, course, dir, urls):
    """
    This function looks through the html and picks out file_ids for all downloadable attachments.
    Then, we search the course object for the respective files using the file_ids to later download them.

    Parameters:
        - loose_html: html obtained from page (whether in modules or assignment)
        - course: course object, obtained after requesting information using the canvasapi
        - directory in which files will be downloaded (this is either the appropriate module or assignment)
        - urls: set of urls that will keep track of all the files we have added
    Returns:
        - None, downloads all attachments on page to hard drive in specified directory
    """
    # Use Beautiful Soup to parse page into readable html to locate links
    parsed_html = BeautifulSoup(loose_html, 'html.parser')

    # Iterate over all <a> and <embed>-tagged objects with href attribute, which iterates over 
    # each link found.
    for a_tag in parsed_html.find_all(['a', 'embed'], href = True):
        file_url = a_tag['href']

        # We check to see if the url fits the format of a file; if it doesn't, we continue on to the next tag.
        if not (r'/files/'in file_url):
            continue

        # Find the id of the file.
        file_url_ls = file_url.split('/')
        file_id = file_url_ls[-1]

        # The file id is usually the very last element; however, if the id is not an int, we need
        # to run a few more checks to verify if the file is obtainable. 

        if not type(file_id) == int:
            # sometimes we will see "?verifier=" representing the temporary access key. To resolve this, 
            # we can simply remove the verifier aspect of the tag. 
            if '?verifier=' in file_id:
                file_id = file_id.split('?')[0]

                # However, sometimes this will NOT be the id, and instead be the phrase "download" or "preview". In this
                # case, the id was the second to last element in the earlier split we did to extract the file.
                if file_id in ['download', 'preview']:
                    file_id = file_url_ls[-2]

            # Sometimes we will see "?wrap". We will skip over these
            elif '?wrap=' in file_id:
                continue
        
            else: #Cannot obtain id; skip this item
                continue

        # Finally, download the files!
        file = course.get_file(file_id)

        download_file(file, dir, urls)
    return 

def valid_filetype(file):
    """
    Given a file, returns a boolean (True or False) depending on whether the file is a type
        we want to download. 
    
    We want the following filetypes:
        - (basically everything)
    
    with the exception of:
        - Videos (.mp4)
    """
    unwanted_filetypes = set(['mp4', 'mov', 'webm', 'wmv', 'flv', 'ogv', 'avi'])
    filetype = file.filename.split('.')[-1].lower()

    return not (filetype in unwanted_filetypes)
# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------

### Load all relevant information into python file
## Locate current operation directory
current_dir = os.path.dirname(os.path.abspath(__file__))

## Load list of course_ids that we are skipping from the .txt file
skip_courses_ls = open(f'{current_dir}/skip_courses.txt', 'r')

# Store course IDs in this set for the classes whose materials you do NOT want to download.
skip_course_ids = set()
for course_id_str in skip_courses_ls.readlines():
    skip_course_ids.add(int(course_id_str))

# Once we have finished this, close the text file and reopen it in append mode to add courses that
# have been downloaded. 
skip_courses_ls.close()
skip_courses_ls = open(f'{current_dir}/skip_courses.txt', 'a')


## Load credentials from the .yaml file
with open(f'{current_dir}/creds.yaml', 'r') as f:
    creds = yaml.safe_load(f)

# Unpack relevant information
API_URL = creds['API_URL']
KEY = creds['KEY']
save_path = creds['SAVE_PATH']

# Initialize new Canvas object and extract user
canvas = Canvas(API_URL, KEY)
user = canvas.get_current_user()


# Go through every course listed under the student; course ids listed at the top will be skipped.
for current_course in canvas.get_courses():

    # Skip the course if it is in the set of courses to be skipped, whether because it has already been
    # downloaded or because we don't want it downloaded. 
    current_id = current_course.id
    if current_id in skip_course_ids:
        continue

    # Additionally, if the course is not published (i.e. not public), continue on to the next 
    # course. We will check for this indirectly by attempting to access the course's name.
    try: 
        print(f'Downloading materials for the following course: {current_course.name}')
    except AttributeError:
        continue


    # Save course file urls in a set; later, we will be iterating through all files in the course,
    # and for the files that we missed, we will be adding them into a separate files folder.
    course_items_urls = set()

    # For this course, create a folder with the name given in the system for the course. 
    course_folder_path = f'{save_path}/{make_valid_folder_name(current_course.name)}'
    if not os.path.exists(course_folder_path):
        os.makedirs(course_folder_path)

    ## Get Module Items
    modules_i = current_course.get_modules()

    # Create a directory for all module items
    modules_dir = f'{course_folder_path}/Modules'

    # Iterate over each module
    for module_i in modules_i:

        # For each module, create yet another sub_directory.
        module_dir = f'{modules_dir}/{make_valid_folder_name(module_i.name)}'

        # For each module, retrieve its items
        module_items = module_i.get_module_items()

        # We are mainly concerned with two types of module items: files and pages.
        # If they are files, we want to download them, no questions asked.
        # If they are pages, we want to access the page and scan it for embedded files we can download.
        # We check for both cases for each module item under this particular module. 
        for module_item in module_items:
            if module_item.type == 'File':

                # Find the item's content id, after which we can find it in the course and directly download.
                module_item_id = module_item.content_id
                file = current_course.get_file(module_item_id)
                download_file(file, module_dir, course_items_urls)

            if module_item.type == 'Page':
                page_url = module_item.page_url
                page = current_course.get_page(page_url)

                # If the page has a body, we can download files from it.
                if page.body:
                    download_files_from_html(page.body, current_course, module_dir, course_items_urls)

    ## Get Assignment Items
    # Create a folder for assignments
    assignments_dir = f'{course_folder_path}/Assignments'

    # Obtain all assignments
    all_assignments = current_course.get_assignments()

    # For each assignment, do the following:
    # 1) Open page url
    # 2) Download all embedded pdfs 
    # 3) Download all submissions
    for assignment in all_assignments:
        assignment_query = assignment
            
        # Open page URL and obtain assignment ID (last element in URL)
        assignment_url = assignment_query.html_url
        assignment_id = assignment_url.split('/')[-1]

        # With ID, obtain assignment
        assignment = current_course.get_assignment(assignment_id)

        # Obtain name of this assignment and create a new folder to save the assignment's materials into
        assignment_dir = f'{assignments_dir}/{make_valid_folder_name(assignment.name)}'

        # Get Page object associated with assignment
        assignment_page = assignment.description

        ## Download all embedded pdfs if the assignment page exists
        if assignment_page:
            download_files_from_html(assignment_page, current_course, assignment_dir, course_items_urls)

    ## Get files stored under the Files section, which we can get via get_folders. 
    Files_dir = f'{course_folder_path}'
    folders = current_course.get_folders()
    for folder in folders:

        # Create folder path combined with the Files_dir
        folder_path = f'{Files_dir}/{folder}'
        
        # Get all the files from each folder, and download the file only if it has not already been
        # downloaded previously.
        folder_files = folder.get_files()

        # Attempt to access the files. If it is forbidden, break out of for loop (we do not have
        # the necessary permissions to download).
        try:
            for file in folder_files:
                download_file(file, folder_path, course_items_urls)
        except Forbidden:
            break
    
    # Once we have downloaded everything from this course, we want to update the text file with 
    # the course id and make sure that it gets saved on the txt file in case of a crash.
    skip_courses_ls.write(str(current_id) + ' \n')    

    # Ensure the changes are saved in case of program crash
    skip_courses_ls.flush()
    os.fsync(skip_courses_ls.fileno())

# After all the courses have been downloaded, we can just close the text file we've been using.
skip_courses_ls.close()


#########################################################
#########################################################
#########################################################
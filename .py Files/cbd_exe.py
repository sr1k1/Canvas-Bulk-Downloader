# Use canvasapi to obtain information from college classes
import os #to create directories to save course material
from canvasapi import Canvas
from canvasapi.exceptions import ResourceDoesNotExist #to raise and intercept errors from file not existing
from canvasapi.exceptions import Forbidden #to catch when we cannot access files of the course directly
from bs4 import BeautifulSoup #to parse HTML into a python-readable format

# Import framework to support executable file, namely tkinter
import threading
import tkinter as tk 
from tkinter import filedialog
from tkinter import messagebox


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
    print(file.display_name)

    # First check to see if the file has already been downloaded; if not, we proceed to download.
    file_url = file.url

    if file_url in urls:
        return
    
    # Now check to see if the file itself has been downloaded in general. 
    # To do so, create the supposed filepath and check!
    file_path = f"{dir}/{make_valid_folder_name(file.display_name, is_file = True)}"
    if os.path.exists(file_path):
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
            msg = f'The file {file.display_name} could not be downloaded. Resource does not exist. \n'
            print(msg)
            return msg

        except MemoryError:
            msg = f'The file {file.display_name} could not be downloaded. The file was either too large to download, or your system does not have enough space. \n'
            print(msg)
            return msg
        
        except:
            msg = f'The file {file.display_name} could not be downloaded. \n'
            print(msg)
            return msg
        
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

# ---------------------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------------------
# WINDOW CONSTRUCTION -------------------------------------------------------------------------

class GUI:
    def __init__(self):

        # Set up main window
        self.window = tk.Tk()

        # Set properties of the window
        self.window.title('Canvas Bulk Downloader')
        self.window.geometry('500x600')
        self.window.resizable(False, False)

        # Create prompt that will show up whenever you are going to close the window (to ensure that
        # nothing is abruptly closed)
        self.window.protocol('WM_DELETE_WINDOW', self.on_click)

        ## We need three parameters from the user: the API URL, the canvas key, and the path where all the 
        ## material will be stored. These will correspond to the following text boxes. 
        
        # API URL:
        self.api_request = tk.Label(self.window, text = 'API URL: ', font = ('Arial Black', 16))
        self.api_request.pack(padx = 10, pady = 10)

        self.api_url = tk.Entry(self.window, font = ('Arial', 12), width = 40)
        self.api_url.pack(padx = 10, pady = 2)

        # Canvas Key:
        self.key_request = tk.Label(self.window, text = 'Key: ', font = ('Arial Black', 16))
        self.key_request.pack(padx = 10, pady = 10)

        self.key = tk.Entry(self.window, font = ('Arial', 12), width = 40)
        self.key.pack(padx = 10, pady = 2)

        # Path:
        self.path_request = tk.Label(self.window, text = 'Path: ', font = ('Arial Black', 16))
        self.path_request.pack(padx = 10, pady = 10)

        self.path = tk.Entry(self.window, font = ('Arial', 12), width = 40)
        self.path.pack(padx = 10, pady = 2)
        
        self.browse_savepath = tk.Button(self.window, text = 'Browse', font = ('Arial', 12), command = self.choose_filepath)
        self.browse_savepath.pack(padx = 10, pady = 10)

        # Once all the information has been input, the bottom button can be hit to begin the process of downloading Canvas material.
        self.download_button_pressed = False
        self.begin_download = tk.Button(self.window, text = 'Download Course Materials', font = ('Arial Black', 12), command = self.download_start)
        self.begin_download.pack(padx = 10, pady = 10)

        # Allow for window to continuously check for input
        self.window.mainloop()

    def choose_filepath(self):
        self.filepath_url = filedialog.askdirectory()
        self.path.delete(0, tk.END)
        self.path.insert(0, self.filepath_url)
        return 
    
    def print_to_window(self, message, txtbx):
        txtbx.delete('1.0', tk.END)
        txtbx.insert('1.0', message)

    def on_click(self):
        if messagebox.askyesno(title = 'Quit?', message = 'Are you sure you want to quit?'):
            self.window.destroy()
    
    def download_start(self):
        if not self.download_button_pressed:
            self.download_button_pressed = True
            threading.Thread(target = self.download_materials, daemon = True).start()

    def download_materials(self):
        # Create three text boxes where the current course, (potential) error messages, and termination status 
        # will be displayed. 
        self.current_course_txtbox = tk.Text(self.window, height = 1, font = ('Arial', 11))
        self.current_course_txtbox.pack(padx = 15, pady = 10)

        self.termination = tk.Text(self.window, height = 1, font = ('Arial', 11))
        self.termination.pack(padx = 15, pady = 10)

        self.error_course_txtbox = tk.Text(self.window, height = 6, font = ('Arial', 11))
        self.error_course_txtbox.pack(padx = 15, pady = 10)

        ## NOTE: The variables defined in this function are not saved as attributes to the class because
        ## they were originally written before the class was created. As such, all variables in this function
        ## will remain LOCAL to the function (unless saved externally in, say, a text file).

        # Save all the relevant pieces of information into variables
        API_URL = self.api_url.get()
        KEY = self.key.get()
        save_path = self.path.get()

        # ---------------------------------------------------------------------------------------------
        # ---------------------------------------------------------------------------------------------
        # Extract the course information itself. Initialize a new Canvas object and extract user
        canvas = Canvas(API_URL, KEY)
        user = canvas.get_current_user()


        # Go through every course listed under the student.
        for current_course in canvas.get_courses():

            # If the course is not published (i.e. not public), continue on to the next 
            # course. We will check for this indirectly by attempting to access the course's name.
            try: 
                current_course_sign = f'Downloading: {current_course.name}'
                print(current_course_sign)
                self.print_to_window(current_course_sign, self.current_course_txtbox)
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

                        file_download_msg = download_file(file, module_dir, course_items_urls)
                        if file_download_msg != None:
                            self.print_to_window(file_download_msg, self.error_course_txtbox)

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
                        file_download_msg = download_file(file, folder_path, course_items_urls)
                        if file_download_msg != None:
                            self.print_to_window(file_download_msg, self.error_course_txtbox)
                except Forbidden:
                    break

        # We can also type to the client that we are done!
        self.print_to_window('All course files have been downloaded!', self.termination)


#########################################################
#########################################################
#########################################################

main_window = GUI()

from dotenv import load_dotenv
load_dotenv()

from common.constants import CONSTANTS
from common.helpers import get_project_root

from AzureMapsCodeSamplesIndexCreation import process_all_samples, process_html_sample2
from AzureMapsDocsIndexCreation import process_all_docs

if __name__ == '__main__':
    fileName = 'azmaps_code_samples_docs.json'
    # Process all documentation
    process_all_docs(save_file_name=fileName)
    
    # Process all code samples
    process_all_samples(process_fun=process_html_sample2, save_file_name=fileName, add_to_existing=True)


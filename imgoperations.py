import io, time
from PIL import Image
from selenium import webdriver
import pathlib

def save_to_png(webfile_name, width = 950, height = 1125 ):  ##, 
    base_name = pathlib.Path(webfile_name).name

    # Import GeckoDriverManager module.
    from webdriver_manager.firefox import GeckoDriverManager
    # Install the GeckoDriverManager to run FireFox web browser.
    driver = webdriver.Firefox(executable_path=GeckoDriverManager().install())
    driver.set_window_size(width, height)

    abs_path = 'C:/Users/nicho/Documents/VocesDeLaFrontera/DemocracyAndPowerInnovation/Python/Common/Results_HTML/'
    outFile = ''.join([abs_path + base_name])
    mapUrl = 'file://{0}'.format(outFile)

    start_time = time.time()
    # your script

    # use selenium to save the html as png image
    driver.get(mapUrl)

    elapsed_time = time.time() - start_time
    print('image loaded:', time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))

    time.sleep(2.0 * elapsed_time)
    print('writing file...')
    abs_path = 'C:/Users/nicho/Documents/VocesDeLaFrontera/DemocracyAndPowerInnovation/Python/Common/Results_IMG/'
    driver.save_screenshot(''.join([abs_path, pathlib.Path(base_name).stem, '.png']))
    print('closing driver...')
    driver.quit()
    print('done...')
    

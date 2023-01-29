import time
import re
import json
import random
from enum import Enum
#from selenium import webdriver
from seleniumwire import webdriver
from seleniumwire.utils import decode

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementNotInteractableException, NoSuchElementException, ElementClickInterceptedException

from dictdiffer import diff as Diff

preferences = []
random.seed(int(time.time()))


driver = webdriver.Firefox()
action = webdriver.ActionChains(driver)


class LIST_DELETE_LOCATIONS(Enum):
    POPUP = 1
    ARRANGE_MODE = 2

class PUBLIC_LIST_TYPES(Enum):
    EDITED = 1
    NOT_EDITED = 2
    ALL = 3

class LIST_TYPES(Enum):
    EDITED = 1
    PRIVATE = 2

def print_json(js):
    print(json.dumps(js, indent=2))

def click_once_clickable(btn):
    try:
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(btn)
        ).click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        driver.execute_script('arguments[0].click();', btn)


def decode_response_body(response):
    return json.loads(decode(response.body, response.headers.get('Content-Encoding', 'identity')))

def reject_cookies():
    try:
        reject_cookies_btn = driver.find_element(By.ID, 'onetrust-reject-all-handler')
        click_once_clickable(reject_cookies_btn)
    except ElementNotInteractableException:
        reject_cookies()
    except NoSuchElementException:
        pass


def click_profile_menu():
    profile_menu_btn = driver.find_element(By.CSS_SELECTOR, '.header__navigationItem--profilePic')
    click_once_clickable(profile_menu_btn)

def log_in():
    def get_email_and_password():
        with open('./account_info.json', 'r') as f:
            obj = json.load(f)
            return obj

    def click_login_btn():
        login_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Log In"]')
        click_once_clickable(login_btn)

    def enter_email():
        email_input = driver.find_element(By.ID, 'username')
        email_input.send_keys(email)

    def enter_password():
        email_input = driver.find_element(By.ID, 'password')
        email_input.send_keys(password)

    def click_continue_btn():
        continue_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Continue"]')
        click_once_clickable(continue_btn)

    def check_login_status():
        def check_email_in_profile_menu():
            call_url = 'https://api.na-backend.odysee.com/api/v1/proxy?m=preference_get'
            pref_get_call = wait_and_return_next_call(call_url, 'POST', first_request_index_to_check = 0)
            preferences.append(decode_response_body(pref_get_call.response))
            time.sleep(3) # Wait for preferences to load, otherwise profile menu closes itself
            click_profile_menu()
            profile_menu = driver.find_element(By.CSS_SELECTOR, '.MuiList-root.MuiList-padding.MuiMenu-list.css-1d5gxrm')
            li_elements = profile_menu.find_elements(By.CSS_SELECTOR, 'li')
            logout_option = li_elements[-1]
            email_span = logout_option.find_element(By.CSS_SELECTOR, '.menu__link-help')
            if (email_span.get_attribute('innerText') == email):
                print('Probably logged in succesfully')
            else:
                print('Probably failed to log in')
        check_email_in_profile_menu()
        click_profile_menu()

    print('Login started')
    email_n_pass = get_email_and_password()
    email = email_n_pass["email"]
    password = email_n_pass["password"]

    click_login_btn()
    enter_email()
    click_login_btn()
    enter_password()
    click_continue_btn()
    check_login_status()

def claim_preview_tile_has_duration(tile):
    has_duration = False
    driver.implicitly_wait(1)
    try: 
        overlay_icon = tile.find_element(By.CSS_SELECTOR, '.claim-preview__overlay-properties')
        duration_span = overlay_icon.find_element(By.CSS_SELECTOR, 'span')
        has_duration = re.match('([0-9]{2}:){1,}[0-9]{2}', duration_span.get_attribute('innerText'))
    except NoSuchElementException:
        pass
    driver.implicitly_wait(10)
    return has_duration

def get_claim_preview_tiles():
    claim_previews = driver.find_elements(By.CSS_SELECTOR, '.claim-preview--tile')
    return claim_previews

def click_3_dot_menu_in_claim_preview_tile(tile):
    menu_btn = tile.find_element(By.CSS_SELECTOR, '.claim__menu-button')
    action.move_to_element(tile)
    action.perform()
    click_once_clickable(menu_btn)

def click_add_to_list_in_3_dot_menu():
    add_to_list_btn = driver.find_element(By.CSS_SELECTOR, '[data-valuetext="Add to Playlist"]')
    click_once_clickable(add_to_list_btn)


def click_new_list_in_save_to_popup():
    new_list_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="New Playlist"]')
    click_once_clickable(new_list_btn)

def enter_name_for_list_in_save_to_popup(name):
    list_name_input = driver.find_element(By.CSS_SELECTOR, '[name="new_collection"]')
    list_name_input.send_keys(name)

def click_confirm_list_creation_in_save_to_popup():
    confirm_btn = driver.find_element(By.CSS_SELECTOR, 'input-submit > [aria-label="Confirm"]')
    click_item_and_wait_preference_set(confirm_btn)

def get_last_responded_call(call_url, method):
    for request in driver.requests.reverse():
        if request.method == method and request.url == call_url and request.response:
            return request
    return None


def wait_and_return_next_call(call_url, method, first_request_index_to_check):
    i = first_request_index_to_check
    requests_count = len(driver.requests)
    while True:
        request = driver.requests[i]
        if request.method == method and request.url == call_url and request.response:
            return request
        if i < requests_count - 1 and (request.url != call_url or request.response): 
            i += 1
        else:
            time.sleep(1)
        requests_count = len(driver.requests)

def get_listable_claim_preview_tile(tiles_to_skip=0):
    for tile in get_claim_preview_tiles():
        if claim_preview_tile_has_duration(tile):
            if tiles_to_skip == 0:
                return tile
            else:
                tiles_to_skip -= 1


def get_latest_preference_diff():
    return Diff(preferences[-2], preferences[-1])

def get_short_claim_name_from_claim_preview_tile(tile):
    tile_href = tile.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
    short_claim_name = tile_href.split('/')[-1].replace(':', '#')
    return short_claim_name

def is_permanent_lbry_url(string):
    return re.match('lbry://[^#]+#[a-f|0-9]{40}$', string)

def is_unix_time_now(unix_time):
    now = int(time.time())
    return (now - 60 < unix_time and
            now + 60 > unix_time)



def test_create_new_list_from_claim_preview():
    refresh_page_and_wait_prefrence_get()
    def check_new_list_was_created_properly():
        try:
            # Check changes in preferences
            diff = list(get_latest_preference_diff())
            assert len(diff) == 1
            assert diff[0][0] == 'add'
            assert diff[0][1] == 'result.shared.value.unpublishedCollections'

            # Check key to the list
            list_id = diff[0][2][0][0]
            list_dict = diff[0][2][0][1]
            assert re.match('[a-f|0-9]{8}(-[a-f|0-9]{4}){3}-[a-f|0-9]{12}', list_id)
            assert list_id == list_dict['id']

            # Check the list value
            assert list_name == list_dict['name']
            assert is_unix_time_now(list_dict['createdAt'])
            assert list_dict['createdAt'] == list_dict['updatedAt']
            assert list_dict['itemCount'] == 1
            assert len(list_dict['items']) == list_dict['itemCount']
            assert is_permanent_lbry_url(list_dict['items'][0])
            assert re.search(short_claim_name, list_dict['items'][0])

            # Few GUI checks
            check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % list_id)
            label = driver.find_element(By.CSS_SELECTOR, 'label[for="select-%s"]' % list_id)
            assert check_box.get_attribute('checked') == 'true'
            assert label.get_attribute('innerText') == list_name

            print('SUCCESS: New list created succestully, with item in it')

        except Exception as e:
            print_json(diff)
            raise e

    print('Testing list creation from claim preview')
    list_name = '0-test-name-%d' % random.randint(1, 999999999) # Random to avoid duplicate names
    claim_preview_tile = get_listable_claim_preview_tile()
    short_claim_name = get_short_claim_name_from_claim_preview_tile(claim_preview_tile)

    click_3_dot_menu_in_claim_preview_tile(claim_preview_tile)
    click_add_to_list_in_3_dot_menu()
    click_new_list_in_save_to_popup()
    enter_name_for_list_in_save_to_popup(list_name)
    click_confirm_list_creation_in_save_to_popup()

    check_new_list_was_created_properly()

def click_close_button():
    close_button = driver.find_element(By.CSS_SELECTOR, '.button--close')
    click_once_clickable(close_button)

def get_random_list_from_latest_stored_preferences(list_type, min_items=0, max_items=99999999):
    key = get_key_for_list_type(list_type)

    lists = preferences[-1]['result']['shared']['value'][key]
    non_empty_list_keys =[]
    for k, v in lists.items():
        items_count = len(v['items'])
        if items_count >= min_items and items_count < max_items:
            non_empty_list_keys.append(k)
    key = non_empty_list_keys[random.randint(0, len(non_empty_list_keys) - 1)]
    return lists[key]

def get_unpublished_list_from_stored_preferences_by_id(list_id, list_type, preference_index=-1):
    if list_type is LIST_TYPES.PRIVATE:
        type_key = 'unpublishedCollections'
    elif list_type is LIST_TYPES.EDITED:
        type_key = 'editedCollections'

    unpublished_list = preferences[preference_index]['result']['shared']['value'][type_key][list_id]
    return unpublished_list

def is_list_checked(list_id):
    check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % list_id)
    return check_box.get_attribute('checked') == 'true'

def click_checkbox_in_save_to_popup(list_id):
    check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % list_id)
    click_item_and_wait_preference_set(check_box)

def check_item_was_added_properly_to_unpublished_list(unpublished_list, list_type, short_claim_name):
    try:
        if list_type is LIST_TYPES.PRIVATE:
            type_key = 'unpublishedCollections'
        elif list_type is LIST_TYPES.EDITED:
            type_key = 'editedCollections'

        diff = list(get_latest_preference_diff())
        assert len(diff) == 3
        assert diff[0][0] == 'change'
        assert diff[0][1] == 'result.shared.value.%s.%s.itemCount' % (type_key, unpublished_list['id'])
        assert (diff[0][2][0] + 1) == diff[0][2][1] # Item count went up

        assert diff[1][0] == 'add'
        assert diff[1][1] == 'result.shared.value.%s.%s.items' % (type_key, unpublished_list['id'])
        assert diff[1][2][0][0] == (diff[0][2][1] - 1) # Placement of item in list(should be last)
        assert is_permanent_lbry_url(diff[1][2][0][1])
        assert re.search(short_claim_name, diff[1][2][0][1])

        assert diff[2][0] == 'change'
        assert diff[2][1] == 'result.shared.value.%s.%s.updatedAt' % (type_key, unpublished_list['id'])
        assert is_unix_time_now(diff[2][2][1])

        # Few GUI checks
        check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % unpublished_list['id'])
        label = driver.find_element(By.CSS_SELECTOR, 'label[for="select-%s"]' % unpublished_list['id'])
        assert check_box.get_attribute('checked') == 'true'
        assert label.get_attribute('innerText') == unpublished_list['name']

        print('SUCCESS: Item added sucessfully')
    except Exception as e:
        print_json(diff)
        raise e

def test_add_items_to_unpublished_list_from_claim_preview(list_type, count_items_to_add):
    refresh_page_and_wait_prefrence_get()
    if list_type is LIST_TYPES.PRIVATE:
        print(f"Testing adding {count_items_to_add} item(s) to private list from claim preview")
    if list_type is LIST_TYPES.EDITED:
        print(f"Testing adding {count_items_to_add} item(s) to edited list from claim preview")

    unpublished_list = get_random_list_from_latest_stored_preferences(list_type)
    for i in range(0, count_items_to_add):
        claim_preview_tile = open_save_to_list_popup_from_listable_claim_preview_tile_that_is_not_in_the_list_and_return_claim_preview_tile(unpublished_list['id'], tiles_to_skip=i)
        short_claim_name = get_short_claim_name_from_claim_preview_tile(claim_preview_tile)
        click_checkbox_in_save_to_popup(unpublished_list['id'])
        check_item_was_added_properly_to_unpublished_list(unpublished_list, list_type, short_claim_name)
        click_close_button()

    return unpublished_list # For deletion test

def refresh_page_and_wait_prefrence_get():
    current_network_requests_count = len(driver.requests)
    driver.get('https://odysee.com')
    call_url = 'https://api.na-backend.odysee.com/api/v1/proxy?m=preference_get'
    wait_and_return_next_call(call_url, 'POST', current_network_requests_count)
    time.sleep(3)

def open_save_to_list_popup_from_listable_claim_preview_tile_that_is_not_in_the_list_and_return_claim_preview_tile(list_id, tiles_to_skip=0):
    found_listable_claim_that_is_not_in_list= False
    tiles_tried = tiles_to_skip
    while not found_listable_claim_that_is_not_in_list:
        claim_preview_tile = get_listable_claim_preview_tile(tiles_to_skip=tiles_tried)
        click_3_dot_menu_in_claim_preview_tile(claim_preview_tile)
        click_add_to_list_in_3_dot_menu()

        found_listable_claim_that_is_not_in_list = not is_list_checked(list_id)
        if not found_listable_claim_that_is_not_in_list:
            click_close_button()
            tiles_tried += 1

    return claim_preview_tile

def get_placement_of_item_in_list(list_items, text_to_match):
    i = 0
    for item in list_items:
        if re.search(text_to_match, item):
            return i
        i += 1

def get_key_for_list_type(list_type):
    if list_type is LIST_TYPES.EDITED:
        key = 'editedCollections'
    elif list_type is LIST_TYPES.PRIVATE:
        key = 'unpublishedCollections'

    return key

def check_item_was_removed_properly_from_unpublished_list(
        private_list_id, list_type, text_to_match_list_item, deleted_from=LIST_DELETE_LOCATIONS.POPUP):
    try:
        diff = list(get_latest_preference_diff())
        prev_list = get_unpublished_list_from_stored_preferences_by_id(private_list_id, list_type, -2)
        list_key = get_key_for_list_type(list_type)
        # Check item count went down
        assert diff[0][0] == 'change', f'Expected "change", got: {diff[0][0]}'
        assert diff[0][1] == 'result.shared.value.%s.%s.itemCount' % (list_key, prev_list['id']),\
            f"Expected 'result.shared.value.{list_key}.{prev_list['id']}.itemCount', got: {diff[0][1]}"
        assert (diff[0][2][0] - 1) == diff[0][2][1], f"Expected '{diff[0][2][0] - 1}', got '{diff[0][2][1]}'"

        # This checks that items after the item removed from the list are moved up by one
        changes_start_index = get_placement_of_item_in_list(list_items=prev_list['items'],
                                                                    text_to_match=text_to_match_list_item)
        changes_end_index = prev_list['itemCount'] - 1 # Last action to items is deletion instead of change
        i = 1
        old_value = prev_list['items'][changes_start_index]
        if diff[i][0] == 'change':
            for list_i in range(changes_start_index, changes_end_index):
                assert diff[i][0] == 'change'
                assert diff[i][1][0] == 'result'
                assert diff[i][1][1] == 'shared'
                assert diff[i][1][2] == 'value'
                assert diff[i][1][3] == list_key
                assert diff[i][1][4] == prev_list['id']
                assert diff[i][1][5] == 'items'
                assert diff[i][1][6] == list_i

                assert len(diff[i][2]) == 2
                assert diff[i][2][0] == old_value
                old_value = diff[i][2][1]
                i += 1

        assert diff[i][0] == "remove"
        assert diff[i][1] == 'result.shared.value.%s.%s.items' % (list_key, prev_list['id'])
        last_index = len(prev_list['items']) - 1
        assert diff[i][2][0][0] == last_index, f"Expected '{last_index}', got: '{diff[i][2][0][0]}'"
        assert diff[i][2][0][1] == old_value
        i += 1

        assert diff[i][0] == 'change'
        assert diff[i][1] == 'result.shared.value.%s.%s.updatedAt' % (list_key, prev_list['id'])
        assert is_unix_time_now(diff[i][2][1])

        # Few GUI checks
        if (deleted_from == LIST_DELETE_LOCATIONS.POPUP):
            check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % prev_list['id'])
            label = driver.find_element(By.CSS_SELECTOR, 'label[for="select-%s"]' % prev_list['id'])
            assert check_box.get_attribute('checked') == None, f"Expected 'false', got: {check_box.get_attribute('checked')}"
            assert label.get_attribute('innerText') == prev_list['name']

        print('SUCCESS: Item removed successfully')
    except Exception as e:
        print_json(diff)
        raise e

def test_add_items_to_unpublished_list_REFRESH_remove_same_item_from_the_list(list_type, count_items_to_add):
    unpublished_list = test_add_items_to_unpublished_list_from_claim_preview(list_type, count_items_to_add) # Returns list it added the item to
    unpublished_list = get_unpublished_list_from_stored_preferences_by_id(unpublished_list['id'], list_type)
    refresh_page_and_wait_prefrence_get()
    print('Testing removing item from private list from claim preview')

    # Find claim tile that's in the list already
    found_listable_claim_that_is_in_list = False
    tiles_tried = 0
    while not found_listable_claim_that_is_in_list:
        claim_preview_tile = get_listable_claim_preview_tile(tiles_to_skip=tiles_tried)
        click_3_dot_menu_in_claim_preview_tile(claim_preview_tile)
        click_add_to_list_in_3_dot_menu()

        found_listable_claim_that_is_in_list = is_list_checked(unpublished_list['id'])
        if not found_listable_claim_that_is_in_list:
            click_close_button()
            tiles_tried += 1

    short_claim_name = get_short_claim_name_from_claim_preview_tile(claim_preview_tile)
    click_checkbox_in_save_to_popup(unpublished_list['id'])

    check_item_was_removed_properly_from_unpublished_list(unpublished_list['id'], list_type, text_to_match_list_item=short_claim_name)

def click_lists_in_side_bar():
    lists_btn = driver.find_element(By.CSS_SELECTOR, '[href="/$/playlists"]')
    click_once_clickable(lists_btn)

def get_collection_list_response_body_by_navigating_to_list_and_refresh_page():
    current_network_requests_count = len(driver.requests)
    call_url = 'https://api.na-backend.odysee.com/api/v1/proxy?m=collection_list'
    click_lists_in_side_bar()
    collection_list_call = wait_and_return_next_call(call_url, 'POST', current_network_requests_count)
    refresh_page_and_wait_prefrence_get()
    collection_list = decode_response_body(collection_list_call.response)
    return collection_list


def get_some_item_from_list(my_list):
    return my_list[random.randint(0, len(my_list) - 1)]


def has_edits(public_list):
    return public_list['claim_id'] in preferences[-1]['result']['shared']['value']['editedCollections']

def get_public_lists_from_latest_collection_list(wanted_type=PUBLIC_LIST_TYPES.ALL):
    collection_list_response = get_collection_list_response_body_by_navigating_to_list_and_refresh_page()
    public_lists = []
    for item in collection_list_response['result']['items']:
        if has_edits(item) and wanted_type is not PUBLIC_LIST_TYPES.NOT_EDITED:
            public_lists.append(item)
        elif not has_edits(item) and wanted_type is not PUBLIC_LIST_TYPES.EDITED:
            public_lists.append(item)
    return public_lists

def get_random_public_list_from_latest_collection_list(wanted_type=PUBLIC_LIST_TYPES.ALL):
    public_lists = get_public_lists_from_latest_collection_list(wanted_type)
    if len(public_lists) < 1:
        input("Could find public list without edits in 10 tries. Exiting...")
        exit()

    return get_some_item_from_list(public_lists)

def do_search_for_text(text):
    search_bar = driver.find_element(By.CSS_SELECTOR, '.wunderbar__input')
    search_bar.send_keys(text)
    search_bar.send_keys(Keys.RETURN)

def remove_item_from_unpublished_list_by_lbry_url(list_id, list_type, lbry_url):
    do_search_for_text(lbry_url)
    click_add_to_list_in_file_page()
    click_checkbox_in_save_to_popup(list_id)
    check_item_was_removed_properly_from_unpublished_list(list_id, list_type, lbry_url)

def click_add_to_list_in_file_page():
    add_to_list_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Add this video to a playlist"]')
    click_once_clickable(add_to_list_btn)

def go_to_list_page(list_id):
    driver.get('https://odysee.com/$/playlist/%s' % list_id)

def search_text_in_lists_page(text):
    search_input = driver.find_element(By.CSS_SELECTOR, '[name="collection_search"]')
    search_input.send_keys(text)

def click_list_in_lists_page(list_id):
    list_url = '/$/playlist/%s' % list_id
    list_link = driver.find_element(By.CSS_SELECTOR, '[href="%s"]' % list_url)
    click_once_clickable(list_link)

def navigate_to_list_page(unpublished_list):
    click_lists_in_side_bar()
    search_text_in_lists_page(unpublished_list['name'])
    click_list_in_lists_page(unpublished_list['id'])

def click_arrange_mode_in_list_page():
    arrange_button = driver.find_element(By.CSS_SELECTOR, 'button[title="Arrange"]')
    click_once_clickable(arrange_button)

def click_item_and_wait_preference_set(item):
    current_network_requests_count = len(driver.requests)
    click_once_clickable(item)
    call_url = 'https://api.na-backend.odysee.com/api/v1/proxy?m=preference_set'
    pref_set_call = wait_and_return_next_call(call_url, 'POST', current_network_requests_count - 1)
    preferences.append(decode_response_body(pref_set_call.response))

def click_delete_on_listitem_on_arrange_mode(li):
    item_url = li.get_attribute('data-rbd-draggable-id')
    delete_btn = li.find_element(By.CSS_SELECTOR, 'button.button-collection-delete')
    click_once_clickable(delete_btn)
    delete_confirm_btn = li.find_element(By.CSS_SELECTOR, 'button.button-collection-delete-confirm')
    click_item_and_wait_preference_set(delete_confirm_btn)

    return item_url

def remove_all_unpublished_list_items_in_arrange_mode(unpublished_list_id, list_type):
    ul = driver.find_element(By.CSS_SELECTOR, 'ul[data-rbd-droppable-id="list__ordering"]')
    lists = ul.find_elements(By.CSS_SELECTOR, 'li')

    for li in lists:
        item_url = click_delete_on_listitem_on_arrange_mode(li)
        check_item_was_removed_properly_from_unpublished_list(unpublished_list_id, list_type, text_to_match_list_item=item_url,
                                                          deleted_from=LIST_DELETE_LOCATIONS.ARRANGE_MODE)

def test_remove_all_items_from_unpublished_list_using_edit(list_type, min_items=0, max_items=99999):
    if list_type is LIST_TYPES.PRIVATE:
        print("Testing removing all items from private list using edit")
    elif list_type is LIST_TYPES.EDITED:
        print("Testing removing all items from edited list using edit")
    refresh_page_and_wait_prefrence_get()
    unpublished_list = get_random_list_from_latest_stored_preferences(list_type, min_items, max_items)
    navigate_to_list_page(unpublished_list)
    click_arrange_mode_in_list_page()
    remove_all_unpublished_list_items_in_arrange_mode(unpublished_list['id'], list_type)

    # Removal of each item is checked separately, if this is reached things should work like expected
    assert is_unpublished_list_empty(unpublished_list['id'], list_type)
    print('SUCCESS: All items removed from the list')

def test_add_item_to_public_list_from_claim_preview():
    def check_item_was_added_properly():
        try:
            diff = list(get_latest_preference_diff())

            assert len(diff) == 1
            assert diff[0][0] == 'add'
            assert diff[0][1] == 'result.shared.value.editedCollections'
            assert diff[0][2][0][0] == public_list['claim_id']

            edited_list = diff[0][2][0][1]
            assert edited_list['id'] == public_list['claim_id']
            assert edited_list['itemCount'] == len(public_list['value']['claims']) + 1

            for i in range(0, len(public_list['value']['claims'])):
                lbry_url_in_edited_list = edited_list['items'][i]
                claim_id_in_public_list = public_list['value']['claims'][i]
                assert is_permanent_lbry_url(lbry_url_in_edited_list)
                assert re.search(claim_id_in_public_list, lbry_url_in_edited_list)

            assert re.search(short_claim_name, edited_list['items'][-1])
            assert edited_list['type'] == 'playlist', f"Expected 'playlist', got: {edited_list['type']}"
            assert is_unix_time_now(edited_list['updatedAt'])

            if 'thumbnail' in public_list['value']:
                assert edited_list['thumbnail']['url'] == public_list['value']['thumbnail']['url']

            if 'title' in public_list['value']:
                assert edited_list['title'] == public_list['value']['title']
                assert edited_list['name'] == public_list['value']['title'],\
                    f"expected '{edited_list['name']}', got: '{public_list['value']['title']}'"

            if 'description' in public_list['value']:
                assert edited_list['description'] == public_list['value']['description']

            # GUI
            check_box = driver.find_element(By.CSS_SELECTOR, 'input#select-%s' % edited_list['id'])
            label = driver.find_element(By.CSS_SELECTOR, 'label[for="select-%s"]' % edited_list['id'])
            assert check_box.get_attribute('checked') == 'true', f"Expected 'None', got: {check_box.get_attribute('checked')}"
            assert label.get_attribute('innerText') == edited_list['name']

            print('SUCCESS: Item added sucessfully')

        except Exception as e:
            print_json(diff)
            raise e

    refresh_page_and_wait_prefrence_get()
    print('Testing adding item to public list from claim preview')
    public_list = get_random_public_list_from_latest_collection_list(wanted_type=PUBLIC_LIST_TYPES.NOT_EDITED)
    claim_preview_tile = open_save_to_list_popup_from_listable_claim_preview_tile_that_is_not_in_the_list_and_return_claim_preview_tile(public_list['claim_id'])
    short_claim_name = get_short_claim_name_from_claim_preview_tile(claim_preview_tile)
    click_checkbox_in_save_to_popup(public_list['claim_id'])

    check_item_was_added_properly()

def is_unpublished_list_empty(list_id, list_type):
    unpublished_list = get_unpublished_list_from_stored_preferences_by_id(list_id, list_type, -1)
    return len(unpublished_list['items']) == 0


def test_remove_all_items_from_unpublished_list_using_file_page(list_type, min_items=0, max_items=99999):
    refresh_page_and_wait_prefrence_get()
    if list_type is LIST_TYPES.PRIVATE:
        print("Testing removing all items from private list using file page")
    elif list_type is LIST_TYPES.EDITED:
        print("Testing removing all items from edited list using file page")

    unpublished_list = get_random_list_from_latest_stored_preferences(list_type, min_items, max_items)
    for lbry_url in unpublished_list['items']:
        remove_item_from_unpublished_list_by_lbry_url(unpublished_list['id'], list_type, lbry_url)

    # Removal of each item is checked separately, if this is reached things should work like expected
    assert is_unpublished_list_empty(unpublished_list['id'], list_type)
    print('SUCCESS: All items removed from the list')


def main():
    driver.get('https://odysee.com')
    driver.implicitly_wait(10)

    reject_cookies()
    log_in() # Also creates first preference state
   # test_create_new_list_from_claim_preview() # Adds the claim to list by default
   # test_add_items_to_unpublished_list_from_claim_preview(LIST_TYPES.PRIVATE, 5)
   # test_add_items_to_unpublished_list_from_claim_preview(LIST_TYPES.EDITED, 3)
    test_add_items_to_unpublished_list_REFRESH_remove_same_item_from_the_list(LIST_TYPES.PRIVATE, 2)
    test_add_items_to_unpublished_list_REFRESH_remove_same_item_from_the_list(LIST_TYPES.EDITED, 1)
   # test_add_item_to_public_list_from_claim_preview()

   # test_remove_all_items_from_unpublished_list_using_file_page(LIST_TYPES.PRIVATE, min_items=1, max_items=5)
   # test_remove_all_items_from_unpublished_list_using_file_page(LIST_TYPES.EDITED, min_items=1, max_items=5)

    # Affected by updatedAt bug
    #test_remove_all_items_from_unpublished_list_using_edit(LIST_TYPES.PRIVATE, min_items=1, max_items=10)
    #test_remove_all_items_from_unpublished_list_using_edit(LIST_TYPES.EDITED, min_items=1, max_items=10)


    input('Press enter to stop(may need to still close window)')


main()

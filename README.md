## New cards workflow
* Input words
* Split words into kanji and radicals
* Check that all kanji are known (interval > 30 days OR tagged as known) for a given word
    * If not tag as locked and suspend
* Check that all radicals are known (interval > 30 days OR tagged as known) for a given kanji
    * If not tag as locked and suspend
* Create CSV for words
* Create CSV for kanji
* Create CSV for radicals

## Check cards workflow
* Get all vocab cards tag locked
* Check for all kanji known
    * If they are tag as new and remove suspended
* Get all kanji cards tagged locked
* Check for all radicals known
    * If they are tag as new and remove suspended
# Rule34 API Basics

You should never receive an error unless the server is overloaded or the search dies. In cases of the searcher breaking, you will receive a response success of "false" and a message stating "search down" or similiar.

## API Keys
**URL to request API key:** [https://rule34.xxx/index.php?page=account&s=options](https://rule34.xxx/index.php?page=account&s=options)

*   **user_id:** Enter the ID of your user
*   **api_key:** The API key

> [!IMPORTANT]
> API limits may be changed at any time. If you run an application that requires higher limits, you can request an unlimited key. This is only applicable for large public project.
> If it's a big Site/App that's more urgent make a ticket on our Discord or alternatively you can site mail staff. [https://rule34.xxx/index.php?page=forum&s=view&id=4240](https://rule34.xxx/index.php?page=forum&s=view&id=4240)
> We reserve the right to disable or deny any key.

## API Terms of service

*   When using the rule34.xxx API or if you serve content from our CDN, you will not display any advertisements or run paywalls. This applies to all bots, apps, and websites.
*   Do not use or request more than one API key. Using multiple keys will result in a suspension of your key or account.

## Endpoints

### Posts List
**Url for API access:** `https://api.rule34.xxx/index.php?page=dapi&s=post&q=index`

| Parameter | Description |
| :--- | :--- |
| `limit` | How many posts you want to retrieve. There is a hard limit of 1000 posts per request. |
| `pid` | The page number. |
| `tags` | The tags to search for. Any tag combination that works on the web site will work here. |
| `cid` | Change ID of the post (Unix time). |
| `id` | The post id. |
| `json` | Set to `1` for JSON formatted response. |
| `fields=tag_info` | Add additional field to all IDs to display tag types. |

### Deleted Images
**Url for API access:** `https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&deleted=show`

*   `last_id`: A numerical value. Will return everything above this number.

### Comments List
**Url for API access:** `https://api.rule34.xxx/index.php?page=dapi&s=comment&q=index`

*   `post_id`: The id number of the comment to retrieve.

### Tags List
**Url for API access:** `https://api.rule34.xxx/index.php?page=dapi&s=tag&q=index`

*   `id`: The tag's id in the database.
*   `limit`: How many tags you want to retrieve. Default limit of 100.

### Autocomplete List
**Url for API access:** `https://rule34.xxx/autocomplete.php?q=`

*   `q`: Enter any letter or incomplete tag. (Not an official endpoint, but useful).

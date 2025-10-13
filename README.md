# tldr-newsletter-slack
Route the TLDR Newsletter(s) to Slack because I don't check my email often enough.
![alt text](image.png)

### Setup

I run the app via a kubernetes deployment in minikube. I have several cronjobs configured to hit it for each desired newsletter. 

First, create a Slack bot, get the token, and save it as a secret in your cluster:

```
k create secret generic slack-api-token --from-literal=token="my-secret-value"
```

Then, create a Slack channel for your newsletter, in the format of `#tldr-newsletter-{newsletter}`, ie `#tldr-newsletter-data`. You can use a different naming convention and just specify the channel name explicitly with the "channel" parameter.

Lastly, apply the resources with `kubectl apply -f k8s/`. 

### Helpers

Create an ad-hoc run
```
kubectl create job --from=cronjob/tldr-data-post-articles tldr-data-post-articles-manual
```

Interact with the API directly
```
kubectl run mycurlpod --image=curlimages/curl -i --tty -- sh
curl -X GET http://tldr-newsletter-slack:5000/articles?newsletter=data
```

See inside the cache database
```
kubectl port-forward svc/postgres 5432:5432
psql -h localhost -p 5432 -U tldr_user -d tldr_cache
```

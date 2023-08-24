# mqttPubSub

### Instructions for setting up and interacting with the system.
Run the following command to start all the services:
`sudo docker compose up`

### A detailed overview of each service and design choices.
1. **Mosquitto MQTT Broker:** This is the mqtt broker (eclipse-mosquitto). Here's the <a href="https://hub.docker.com/_/eclipse-mosquitto">documentation</a>.
2. **Publisher:** The publisher publishes message to the broker, the topic can be configured in .env file by default it is `temperatureReadings`. The number of publishers and the rate at which each device pub;ishes data can also be configured in the .env file.
3. **Subscriber:** The subscriber subcribes to a given topic and the moment it receives a message, it is pushed to a queue. A worker thread is listening to the queue and it updates the latest readings in redis and when the number of readings reaches the `BATCH_SIZE`, it pushes the batch to mongo. By default the Nnumber of workers is set to 1 and batch size is set to 100, both of which can be configured in the .env config file.
4. **Redis:** This is the <a href="https://hub.docker.com/_/redis">official redis docker image</a> available on docker hub.
5. **MongoDB:** This is the <a href="https://hub.docker.com/_/mongo">official mongo docker image</a> available on docker hub.
6. **API:** The API is written using FastAPI.  It has following 2 end-points:
   * An endpoint that allows users to fetch sensor readings by specifying a start and end range. Sample request: `http://172.18.0.7:8000/readings/?sensor_id=1&start=2023-08-20T00:00:00&end=2023-08-24T00:00:00`
   * An endpoint to retrieve the last ten sensor readings for a specific sensor. Sample request: `http://172.18.0.7:8000/readings/10`
   The API is using Basic Authentication with dummy username set to 'user' and password set to 'password', these can also be configured from the `api/main.py`. Basic Auth was chosen for the sake of simplicity, otherwise JWT based authentication is obviously a better choice.
### Sending request to the API endpoints
1. List docker containers:
`sudo docker ps`
2. Copy the ID of the container named `mqttsensorsimulator-api`
3. Get the IP address:
`sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' container_id_or_name`
4. Hit the endpoit using the IP address like this. Suppose the IP address is `172.18.0.7`, the the requests would be:
`http://172.18.0.7:8000/readings/?sensor_id=1&start=2023-08-20T00:00:00&end=2023-08-24T00:00:00`

and

`http://172.18.0.7:8000/readings/10`

**Don't forget to add Authentication**.

### Challenges
Setting the network for the services to communicate with each other was the most challenging part.

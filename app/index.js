express = require('express');
mongodb = require('mongodb');
var mongoClient = mongodb.MongoClient;
var url = "mongodb://localhost:27017/jeopardy"
var database;
const app = express();
console.log("Hello World");

app.get('/', (req, res) => res.send('Hello World!\n'));
app.get('/mongo/', (req, res) => findDocuments(database, function(result){res.send("Done.\n")}));
app.post('/mongo/', (req, res) => insertDocuments(database, function(result){res.send("Done.\n")}));

var insertDocuments = function(db, callback) {
	var collection = db.collection('documents');
	collection.insertMany([
		{name : "Riley"}, {name : "Jesse"}, {name : "Jim"}
	], function(err, result) {
		console.log(err);
		console.log(result.result.n);
		console.log(result.ops.length);
		console.log("Inserted docs.\n");
		callback(result);
	});
}

var findDocuments = function(db, callback) {
	var collection = db.collection('documents');
	collection.find({}).toArray(function(err, docs) {
		console.log(err);
		console.log(docs);
		console.log("Found docs.\n");
		callback(docs);
	});
}

var gracefulShutdown = function() {
	console.log("Shutting down...");
	database.close();
	process.exit();
}
process.on('SIGTERM', gracefulShutdown);
process.on('SIGINT', gracefulShutdown);

mongoClient.connect(url, function(err, db) {
	if (err) throw err;
	console.log("Database Created!");
	database = db;
});
app.listen(3000, () => console.log('Example app listening on port 3000!'));
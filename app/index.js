express = require('express');
mongodb = require('mongodb');
var mongoClient = mongodb.MongoClient;
var url = "mongodb://localhost:27017/jeopardy"
var database;
var collection_name = "games"
const app = express();
console.log("Hello World");

app.get('/', (req, res) => res.send('Hello World!\n'));
app.get('/mongo/', (req, res) => findDocuments(database, function(result){res.send(result)}));
app.get('/mongo/:id', (req, res) => findDocument(req.params.id, database, function(result){res.send(result)}));
app.post('/mongo/', (req, res) => insertDocuments(database, function(result){res.send("Done.\n")}));
app.delete('/mongo/', (req, res) => dropCollection(database, function(result){res.send("Deleted.\n")}));
app.delete('/mongo/:id', (req, res) => deleteElement(req.params.id, database, function(result){res.send("Deleted.\n")}));

var insertDocuments = function(db, callback) {
	var collection = db.collection(collection_name);
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
	var collection = db.collection(collection_name);
	collection.find({}).toArray(function(err, docs) {
		console.log(err);
		console.log(docs);
		console.log("Found docs.\n");
		callback(docs);
	});
}

var findDocument = function(id, db, callback) {
	var collection = db.collection(collection_name);
	collection.find({_id:id}).toArray(function(err, docs) {
		console.log(err);
		console.log(docs);
		console.log("Found docs.\n");
		callback(docs[0]);
	});
}

var dropCollection = function(db, callback) {
	var collection = db.collection(collection_name);
	collection.drop((function(err, delOK) {
	    if (err) throw err;
	    if (delOK) console.log("Collection deleted");
		callback(delOK);
	}));
}

var deleteElement = function(id, db, callback) {
	var collection = db.collection(collection_name);
	collection.deleteOne({_id:id},(function(err, delOK) {
	    if (err) throw err;
	    if (delOK) console.log(id," deleted");
		callback(delOK);
	}));
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
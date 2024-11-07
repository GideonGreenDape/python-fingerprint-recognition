const express = require('express');
const multer = require('multer');
const { MongoClient } = require('mongodb');
const cors = require('cors');
const { spawn } = require('child_process')
const app = express();
const fs = require('fs');
require('dotenv').config();
const path = require('path');
const os = require('os');
const sharp = require('sharp');



const port = process.env.PORT || 5000;
const tempDir = os.tmpdir();
const corsOptions = {
    origin: 'http://localhost:5173',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    credentials: true,
    allowedHeaders: ['Content-Type', 'Authorization'],
};



// Middleware

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Setup multer for handling multiple fields
const storage = multer.memoryStorage();
const upload = multer({ storage }).fields([
    { name: 'profilePhoto', maxCount: 1 },
]);

// Setup CORS to handle preflight requests for all routes
app.use(cors(corsOptions));
app.options('*', cors(corsOptions)); // Allow preflight for all routes

// MongoDB Connection URI
const client = new MongoClient(process.env.MONGODB_URI);

// Endpoint to handle multipart/form-data
app.post('/upload', upload, async (req, res) => {
    console.log(req.body);
    console.log("Request files:", req.files);

    try {
        // Handle the profile photo
        const profilePhotoBuffer = req.files['profilePhoto'] ? req.files['profilePhoto'][0].buffer : null;

        // Convert fingerprint image to base64 and validate if it exists
        let fingerprintBase64;
        if (req.body.fingerprintImage) {
            fingerprintBase64 = req.body.fingerprintImage.replace(/^data:image\/png;base64,/, "");
            if (!isValidBase64(fingerprintBase64)) {
                return res.status(400).json({ message: 'Invalid fingerprint image format.' });
            }
        } else {
            fingerprintBase64 = null;
        }

        // Spawn Python process
        const pythonProcess = spawn('python', [path.join(__dirname, 'processor.py')]);

        // Write the base64 fingerprint data to the Python process via stdin
        pythonProcess.stdin.write(fingerprintBase64);
        pythonProcess.stdin.end();
 
        let dataBuffer = '';

        // Listen for data output (the descriptors) from the Python script
        pythonProcess.stdout.on('data', async (data) => {
            // Concatenate data as it's being streamed
            dataBuffer += data.toString();
        });
        
            // Once the stream ends, process the data
            pythonProcess.stdout.on('end', async () => {
                try {
                    // Parse the accumulated buffer as JSON
                    const descriptors = JSON.parse(dataBuffer);
                    console.log(descriptors);
        
                    // Prepare data to insert into MongoDB
                    const sampleData = {
                        firstName: req.body.firstName,
                        lastName: req.body.lastName,
                        middleName: req.body.middleName,
                        profilePhoto: profilePhotoBuffer, // Store image as Buffer
                        fingerprintDescriptors: descriptors, // Store only descriptors instead of fingerprint image
                        uploadedAt: new Date(),
                    };
        
                    // Connect to MongoDB and insert the data
                    await client.connect();
                    const database = client.db('designsbyese');
                    const collection = database.collection('samples');
        
                    // Insert data into MongoDB
                    const result = await collection.insertOne(sampleData);
                    console.log('Sample data stored:', result);
        
                    // Send success response with the inserted ID
                    res.status(200).json({ message: 'Sample uploaded successfully', id: result.insertedId });
                } catch (e) {
                    // Handle errors (e.g., JSON parse errors)
                    console.error('Error parsing JSON:', e);
                    res.status(500).json({ message: 'Error processing fingerprint descriptors' });
                }
            });
     
        
        // Handle errors from the Python process
        pythonProcess.stderr.on('data', (error) => {
            console.error('Error in descriptor extraction:', error.toString());
            res.status(500).json({ message: 'Error in processing fingerprint' });
        });

    } catch (error) {
        console.error('Error uploading sample:', error);
        res.status(500).json({ message: 'Error uploading sample', error: error.message });
    } finally {
        // Close the MongoDB connection
        await client.close();
    }
});

// Function to check if a base64 string is valid
function isValidBase64(str) {
    // Check if the string is a valid base64 encoded string
    const regex = /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/;
    return regex.test(str);
}






app.post('/validatefingerprint', async (req, res) => {
    console.log(req.body);

    const { imageFile } = req.body;

    if (!imageFile) {
        return res.status(400).json({
            message: 'No fingerprint image provided.',
        });
    }

    try {
        // Connect to MongoDB
        await client.connect();
        const database = client.db('designsbyese');
        const collection = database.collection('samples');

        // Retrieve all fingerprint descriptors and user data from MongoDB
        const fingerprints = await collection.find({}, {
            projection: { firstName: 1, lastName: 1, middleName: 1, profilePhoto: 1, fingerprintDescriptors: 1 }
        }).toArray();

        if (fingerprints.length === 0) {
            return res.status(404).json({ message: 'No fingerprints found in the database.' });
        }

        // Write uploaded fingerprint to a temporary file
        const uploadedFingerprintPath = path.join(tempDir, 'uploaded_fingerprint.png');
        const base64Regex = /^data:image\/(?:png|jpeg|jpg);base64,/;
        const base64Data = imageFile.replace(base64Regex, '');

        // Save uploaded fingerprint as a binary .png file
        await fs.promises.writeFile(uploadedFingerprintPath, base64Data, { encoding: 'base64' });

        // Collect all stored fingerprint descriptors from the database
        const storedDescriptors = fingerprints.map(fp => fp.fingerprintDescriptors);

        // Write descriptors to a temporary file
        const descriptorsFilePath = path.join(tempDir, 'descriptors.json');
        await fs.promises.writeFile(descriptorsFilePath, JSON.stringify(storedDescriptors));

        // Spawn Python process to compare fingerprints using descriptors
        const pythonProcess = spawn('python', [path.join(__dirname, 'compare.py'), uploadedFingerprintPath, descriptorsFilePath]);

        let dataFromPython = '';
        pythonProcess.stdout.on('data', (data) => {
            dataFromPython += data.toString();
        });

        pythonProcess.on('close', async (code) => {
            if (code !== 0) {
                console.error(`Python process exited with code ${code}`);
                return res.status(500).json({ message: 'Error during fingerprint validation.' });
            }

            try {
                const result = JSON.parse(dataFromPython);
                console.log(result);

                // Define a threshold for match percentage 
                const matchThreshold = 70;

                // Handle the case when no match is found or the match percentage is below the threshold
                if (result.matchIndex === -1 || result.matchPercentage < matchThreshold) {
                    return res.status(404).json({
                        message: 'No fingerprint match found.',
                    });
                }

                const matchedUser = fingerprints[result.matchIndex];

                // Return matched user details along with the match percentage
                return res.json({
                    message: 'Fingerprint match found',
                    firstName: matchedUser.firstName,
                    lastName: matchedUser.lastName,
                    middleName: matchedUser.middleName,
                    profilePicture: matchedUser.profilePhoto,
                    matchPercentage: result.matchPercentage,
                });

            } catch (error) {
                console.error('Error parsing Python output:', error);
                return res.status(500).json({ message: 'Error parsing fingerprint match result.' });
            }
        });

        pythonProcess.stderr.on('data', (data) => {
            console.error(`Python error: ${data}`);
            return res.status(500).json({ message: 'Error during fingerprint validation.' });
        });

    } catch (error) {
        console.error('Error validating fingerprint:', error);
        return res.status(500).json({ message: 'Error validating fingerprint. Please try again.' });
    } finally {
        await client.close();
    }
});





// Start the server
app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});

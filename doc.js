const express = require('express');
const multer = require('multer');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const path = require('path');
const fs = require('fs');

puppeteer.use(StealthPlugin());

const app = express();
const PORT = process.env.PORT || 3000;

// Global browser instance
let browser = null;
let page = null;

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const uploadsDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir, { recursive: true });
    }
    cb(null, uploadsDir);
  },
  filename: function (req, file, cb) {
    // Keep original filename
    cb(null, file.originalname);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 4 * 1024 * 1024 * 1024
  }
});

// Initialize browser on startup
async function initializeBrowser() {
  try {
    console.log('Initializing browser...');
    const userDataDir = '/home/go/.config/google-chrome';
    
    browser = await puppeteer.launch({
      headless: false,
      userDataDir,
      args: [
        '--profile-directory=Default',
        '--disable-blink-features=AutomationControlled',
        '--no-default-browser-check'
      ]
    });
    
    page = await browser.newPage();
    await page.goto('https://vk.com/docs', { waitUntil: 'domcontentloaded' });
    console.log('Browser initialized and navigated to VK docs');
    
  } catch (error) {
    console.error('Failed to initialize browser:', error);
    throw error;
  }
}

// Middleware
app.use(express.json());

// Upload endpoint
app.post('/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ 
        error: 'No file uploaded. Please include a file in the "file" field.' 
      });
    }

    // Check if browser is still alive
    if (!browser || !page) {
      return res.status(500).json({ 
        error: 'Browser not initialized. Please restart the server.' 
      });
    }

    const filePath = req.file.path;
    const fileName = req.file.filename;
    
    console.log(`Processing upload: ${fileName}`);
    
    // Call the VK upload function
    const docUrl = await uploadToVK(filePath, fileName);
    
    // Clean up uploaded file
    fs.unlinkSync(filePath);
    
    if (docUrl) {
      res.json({ 
        success: true, 
        url: docUrl,
        filename: fileName
      });
    } else {
      res.status(500).json({ 
        error: 'Failed to upload file to VK' 
      });
    }
    
  } catch (error) {
    console.error('Upload error:', error);
    
    // Clean up file if it exists
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    
    res.status(500).json({ 
      error: 'Internal server error',
      message: error.message 
    });
  }
});

// VK upload function (refactored to use persistent browser)

// VK upload function (refactored to use persistent browser)
async function uploadToVK(filePath, fileName) {
  try {
    // Navigate to docs page (in case we're not there)
  
    
    // Wait for and click the real upload button in the header
    const uploadBtnSelector = '#spa_root > div > div:nth-child(2) button';
    await page.waitForSelector(uploadBtnSelector, { visible: true });
    await page.click(uploadBtnSelector);
    console.log('Clicked upload button');
    
    // Wait for modal title "Upload file"
    await page.waitForSelector('[data-testid="modalheader-title"]', { visible: true });
    const modalTitle = await page.$eval('[data-testid="modalheader-title"]', el => el.textContent);
    console.log('Modal Title:', modalTitle);
    
    // Upload the file
    const inputSelector = 'input[type="file"].flat_button_file';
    await page.waitForSelector(inputSelector);
    const fileInput = await page.$(inputSelector);
    await fileInput.uploadFile(filePath);
    console.log('Upload started:', filePath);
    
    // Wait for the Save button to become clickable (upload completed)
    await page.waitForSelector('[data-testid="docs_modal_save_button"]:not([disabled])', { 
      visible: true, 
      timeout: 300000 
    });
    console.log('Upload completed, Save button is ready');
    
    // Click the Save button
    await page.click('[data-testid="docs_modal_save_button"]');
    console.log('Clicked Save button');
    
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Wait for file cells to be visible and get the uploaded doc URL
    await page.waitForSelector('[data-testid="file_cell"]', { visible: true });
    
    // Get ALL file cells (this returns an array)
    const fileCells = await page.$$('[data-testid="file_cell"]');
    console.log(`Found ${fileCells.length} file cells`);
    
    // Find the file cell with matching title
    for (const cell of fileCells) {
      try {
        const title = await cell.$eval('.vkitFileCell__title--Z0bxt', el => el.textContent.trim());
        console.log(`Checking file: ${title}`);
        
        if (title === fileName) {
          const docUrl = await cell.evaluate(el => el.href);
          console.log('Uploaded doc URL:', docUrl);
          return docUrl;
        }
      } catch (cellError) {
        console.error('Error processing cell:', cellError);
        continue;
      }
    }
    
    // Alternative approach: try to find the file in a different way
    console.log('File not found in first attempt, trying alternative approach...');
    
    // Wait a bit more and try again
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Try to find any links that might contain the document
    const allLinks = await page.$$('a[href*="/doc"]');
    console.log(`Found ${allLinks.length} document links`);
    
    for (const link of allLinks) {
      try {
        const linkText = await link.evaluate(el => el.textContent.trim());
        const href = await link.evaluate(el => el.href);
        console.log(`Checking link: ${linkText} -> ${href}`);
        
        if (linkText.includes(fileName)) {
          console.log('Found uploaded doc URL via alternative method:', href);
          return href;
        }
      } catch (linkError) {
        console.error('Error processing link:', linkError);
        continue;
      }
    }
    
    throw new Error('Could not find uploaded file URL');
    
  } catch (error) {
    console.error('VK upload error:', error);
    throw error;
  }
}
// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

// Start server with browser initialization
async function startServer() {
  try {
    // Initialize browser first
    await initializeBrowser();
    
    // Start the server
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`Server running on 0.0.0.0:${PORT}`);
      console.log(`Upload endpoint: http://0.0.0.0:${PORT}/upload`);
      console.log(`Health check: http://0.0.0.0:${PORT}/health`);
    });
    
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down gracefully');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});
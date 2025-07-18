const express = require('express');
const multer = require('multer');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const path = require('path');
const fs = require('fs');

puppeteer.use(StealthPlugin());

const app = express();
const PORT = process.env.PORT || 3000;

let browser = null;
let page = null;

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    const uploadsDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadsDir)) {
      fs.mkdirSync(uploadsDir, { recursive: true });
    }
    cb(null, uploadsDir);
  },
  filename: function (req, file, cb) {
    cb(null, file.originalname);
  }
});

const upload = multer({
  storage: storage,
  limits: {
    fileSize: 4 * 1024 * 1024 * 1024 // 4GB limit
  }
});

async function initializeBrowser() {
  try {
    console.log('Initializing browser...');
    const userDataDir = '/home/go/.config/google-chrome';

    browser = await puppeteer.launch({
      headless: false,
      userDataDir,
      args: [
        '--profile-directory=Profile 2',
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

app.use(express.json());

app.post('/upload', upload.single('file'), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      error: 'No file uploaded. Please include a file in the "file" field.'
    });
  }

  if (!browser || !page) {
    return res.status(500).json({
      error: 'Browser not initialized. Please restart the server.'
    });
  }

  const filePath = req.file.path;
  const fileName = req.file.filename;
  let docUrl = null;
  let attempts = 0;
  const maxAttempts = 3;

  console.log(`Processing upload: ${fileName}`);

  while (attempts < maxAttempts) {
    attempts++;
    try {
      docUrl = await uploadToVK(filePath, fileName);
      break; // Success, exit loop
    } catch (uploadError) {
      console.error(`Upload attempt ${attempts} failed:`, uploadError);

      if (attempts >= maxAttempts) {
        // Max attempts reached, fail the request
        if (req.file && fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
        }
        return res.status(500).json({
          error: 'Failed to upload file to VK after multiple attempts',
          message: uploadError.message
        });
      }

      // Retry: refresh the page and wait before retrying
      try {
        console.log('Refreshing page before retrying...');
        await page.reload({ waitUntil: 'domcontentloaded' });
        // Wait a bit to let the page settle
        await new Promise(resolve => setTimeout(resolve, 5000));
      } catch (reloadError) {
        console.error('Error refreshing page:', reloadError);
        // If reload fails, still try the next attempt anyway
      }
    }
  }

  fs.unlinkSync(filePath);

  if (docUrl) {
    res.json({
      success: true,
      url: docUrl,
      filename: fileName
    });
  }
});
async function uploadToVK(filePath, fileName) {
  try {
    const uploadBtnSelector = '#spa_root > div > div:nth-child(2) button';
    await page.waitForSelector(uploadBtnSelector, { visible: true });
    await page.click(uploadBtnSelector);
    console.log('Clicked upload button');

    await page.waitForSelector('[data-testid="modalheader-title"]', { visible: true });
    const modalTitle = await page.$eval('[data-testid="modalheader-title"]', el => el.textContent);
    console.log('Modal Title:', modalTitle);

    const inputSelector = 'input[type="file"].flat_button_file';
    await page.waitForSelector(inputSelector);
    const fileInput = await page.$(inputSelector);
    await fileInput.uploadFile(filePath);
    console.log('Upload started:', filePath);

    await page.waitForSelector('[data-testid="docs_modal_save_button"]:not([disabled])', {
      visible: true,
      timeout: 400000
    });

    const detailedSelector = '#box_layer > div.popup_box_container.popup_box_container--no-body.popup_box_container--no-shadow > div > div.vkui__root > div > div.vkitModalBody__container--vC7yA.vkitModalBody__containerLevel1--nh7zX > form > div:nth-child(2) > div > label:nth-child(4) > span';

    await page.waitForSelector(detailedSelector, { visible: true });
    await page.click(detailedSelector);
    console.log('Upload completed, Save button is ready');

    // Removed invalid page.$eval() line here

    await page.click('[data-testid="docs_modal_save_button"]');
    console.log('Clicked Save button');

    await new Promise(resolve => setTimeout(resolve, 3000));

    await page.waitForSelector('[data-testid="file_cell"]', { visible: true });

    const fileCells = await page.$$('[data-testid="file_cell"]');
    console.log(`Found ${fileCells.length} file cells`);

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

    console.log('File not found in first attempt, trying alternative approach...');
    await new Promise(resolve => setTimeout(resolve, 2000));

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

app.get('/health', (req, res) => {
  res.json({ status: 'OK', timestamp: new Date().toISOString() });
});

async function startServer() {
  try {
    await initializeBrowser();

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

startServer();

process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down gracefully');
  if (browser) await browser.close();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down gracefully');
  if (browser) await browser.close();
  process.exit(0);
});
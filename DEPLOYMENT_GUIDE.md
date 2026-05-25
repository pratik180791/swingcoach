# SwingCoach Deployment & Usage Guide

This guide will walk you through deploying your personal AI Swing Trading Coach. The system is designed to be **100% free** and requires **zero server maintenance**. 

There are two parts to this deployment:
1. **The Brain (GitHub)**: Setting up the automated daily data fetching and analysis.
2. **The App (Android)**: Building and installing the app on your phone.

---

## Part 1: Setting up "The Brain" (GitHub)

The Python engine runs automatically on GitHub Actions every weekday at 4:30 PM ET and publishes the results to GitHub Pages.

### Step 1: Create the Repository
1. Go to [GitHub.com](https://github.com/) and log in (or create a free account).
2. Click the **"+"** icon in the top right and select **"New repository"**.
3. Name it `swingcoach` (or whatever you prefer).
4. Make sure it is set to **Public** (required for free GitHub Pages).
5. Do NOT check "Add a README file". Click **"Create repository"**.

### Step 2: Upload the Code
1. Extract the `swingcoach_repo.zip` file you downloaded.
2. Open the extracted folder on your computer.
3. On your new GitHub repository page, click **"uploading an existing file"**.
4. Drag and drop **all** the files and folders from the extracted folder into the browser.
5. Click **"Commit changes"**.

### Step 3: Enable GitHub Pages (The Data Host)
1. In your GitHub repository, click on the **Settings** tab.
2. On the left sidebar, scroll down and click on **Pages**.
3. Under "Build and deployment", look for the **Source** dropdown and select **Deploy from a branch**.
4. Under the **Branch** section, select `main` from the first dropdown, and `/docs` from the second dropdown.
5. Click **Save**.
6. Wait 1-2 minutes. Refresh the page. At the top, you should see a message like: *"Your site is live at https://YOUR_USERNAME.github.io/swingcoach"*. Keep this URL handy.

### Step 4: Enable the Automated Daily Run
1. In your GitHub repository, click on the **Actions** tab.
2. You will see a message saying "Workflows aren't being run on this forked repository". Click the green button that says **"I understand my workflows, go ahead and enable them"**.
3. On the left sidebar, click on **"SwingCoach Daily Briefing"**.
4. Click the **"Run workflow"** button on the right side, then click the green **"Run workflow"** button to trigger the first manual run.
5. Wait about 30 seconds for it to finish (it will turn green). The system is now live! It will automatically run every Monday–Friday at 4:30 PM ET.

---

## Part 2: Building "The App" (Android)

The Android app is built using React Native (Expo). It reads the data published by your GitHub Pages site.

### Step 1: Connect the App to Your GitHub
Before building the app, you need to tell it where to find your data.
1. On your computer, open the `android_app/SwingCoach/src/services/briefingFetcher.ts` file in any text editor (like Notepad or VS Code).
2. Find line 4: 
   `const GITHUB_USERNAME = 'YOUR_USERNAME';`
3. Change `YOUR_USERNAME` to your actual GitHub username (e.g., `const GITHUB_USERNAME = 'johndoe';`).
4. Find line 5:
   `const REPO_NAME = 'swingcoach_repo';`
5. Change `swingcoach_repo` to whatever you named your repository in Step 1 (e.g., `const REPO_NAME = 'swingcoach';`).
6. Save the file.

### Step 2: Build the APK (Free via Expo EAS)
You don't need Android Studio. You can build the app in the cloud for free using Expo.
1. You need [Node.js](https://nodejs.org/) installed on your computer.
2. Open a terminal (Command Prompt on Windows, Terminal on Mac).
3. Navigate to the app folder:
   `cd path/to/extracted/swingcoach_repo/android_app/SwingCoach`
4. Install the dependencies by running:
   `npm install`
5. Install the Expo CLI by running:
   `npm install -g eas-cli`
6. Log in to Expo (or create a free account):
   `eas login`
7. Build the Android APK by running:
   `eas build -p android --profile preview`
8. The terminal will give you a link to a webpage where you can watch the build progress. It usually takes 5-10 minutes.
9. When it's done, the webpage will give you a link to **Download the APK**.

### Step 3: Install on Your Phone
1. Download the APK file to your Android phone (you can email it to yourself, use Google Drive, or connect via USB).
2. Tap the APK file on your phone to install it. 
   *(Note: Your phone may warn you about installing apps from "Unknown Sources". You will need to go to Settings and allow it for this installation).*
3. Open the **SwingCoach** app!

---

## How to Use It Daily

1. **4:00 PM ET**: The stock market closes. Pradeep Bhonde updates his MM Google Sheet shortly after.
2. **4:30 PM ET**: Your GitHub Action automatically wakes up, reads the new data, runs the coaching logic, and updates your GitHub Pages site.
3. **Evening**: You open the SwingCoach app on your phone. It instantly pulls the latest briefing.
4. **Action**: Read the Dashboard. If it says "Scan Tonight: YES", look at the scan parameters, read the mental anchor, take 60 seconds to breathe, and then go to your PC and run your Qullamaggie momentum scans. If it says "Scan Tonight: NO", close your laptop and enjoy your evening.

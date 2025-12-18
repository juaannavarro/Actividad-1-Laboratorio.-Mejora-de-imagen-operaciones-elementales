import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import glob

def load_images():
    images = []
    # Load 1.png to 4.png from 'fotos_carga'
    for i in range(1, 5):
        path = f"fotos_carga/{i}.png"
        if os.path.exists(path):
            img = cv2.imread(path)
            if img is not None:
                images.append((str(i), img))
            else:
                print(f"Warning: Could not read {path}")
        else:
            print(f"Warning: File {path} not found")
    return images

def adjust_gamma(image, gamma=1.0):
    # We want gamma < 1.0 to brighten the image.
    # Standard formula: O = I^(gamma)
    # If gamma=0.5 -> O = I^0.5 (Sqrt) -> Brightens
    table = np.array([((i / 255.0) ** gamma) * 255
                      for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def log_transform(image):
    # Convert to float to avoid overflow/underflow
    img_float = np.float32(image)
    # c = 255 / log(1 + max_pixel_value)
    # For a full range image max is 255. But our images are dark.
    # We can assume we want to stretch to full 255.
    c = 255 / np.log(1 + np.max(img_float))
    log_image = c * (np.log(img_float + 1))
    
    # Normalize to 0-255 explicitly to ensuring full brightness usage
    log_image = cv2.normalize(log_image, None, 0, 255, cv2.NORM_MINMAX)
    
    return np.uint8(log_image)

def histogram_equalization(image):
    # Convert to YUV to equalized only Y channel
    img_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    return cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

def clahe_equalization(image, clip_limit=2.0):
    img_yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
    img_yuv[:,:,0] = clahe.apply(img_yuv[:,:,0])
    return cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

def unsharp_mask(image, sigma=1.0, strength=1.5):
    gaussian = cv2.GaussianBlur(image, (0, 0), sigma)
    unsharp_image = cv2.addWeighted(image, 1.0 + strength, gaussian, -strength, 0)
    return unsharp_image

def plot_comparison(name, original, processed, title, filename):
    # Convert BGR to RGB for matplotlib
    orig_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
    proc_rgb = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle(f"Image {name}: {title}", fontsize=16)

    # Images
    axes[0, 0].imshow(orig_rgb)
    axes[0, 0].set_title("Original")
    axes[0, 0].axis('off')

    axes[0, 1].imshow(proc_rgb)
    axes[0, 1].set_title(f"Processed ({title})")
    axes[0, 1].axis('off')

    # Histograms
    colors = ('b', 'g', 'r')
    for i, col in enumerate(colors):
        hist_orig = cv2.calcHist([original], [i], None, [256], [0, 256])
        axes[1, 0].plot(hist_orig, color=col)
        
        hist_proc = cv2.calcHist([processed], [i], None, [256], [0, 256])
        axes[1, 1].plot(hist_proc, color=col)

    axes[1, 0].set_title("Original Histogram")
    axes[1, 0].set_xlim([0, 256])
    
    axes[1, 1].set_title("Processed Histogram")
    axes[1, 1].set_xlim([0, 256])

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def save_clean_comparison(name, original, processed, filename):
    # Create a simple side-by-side concatenation
    # Ensure processed size matches original (should be same, but safety first)
    h, w, c = original.shape
    processed_resized = cv2.resize(processed, (w, h))
    
    # Add a small white separator for aesthetics
    separator = np.ones((h, 20, 3), dtype=np.uint8) * 255
    
    combined = np.hstack((original, separator, processed_resized))
    cv2.imwrite(filename, combined)

def main():
    output_dir = "fotos_result"
    os.makedirs(output_dir, exist_ok=True)
    
    images = load_images()
    
    if not images:
        print("No images found to process.")
        return

    print(f"Found {len(images)} images. Processing...")

    for name, img in images:
        print(f"Processing Image {name}...")
        
        # Default Params (Works well for Image 2)
        params = {
            'gamma': 0.5,
            'clahe_clip': 3.0,
            'unsharp_sigma': 2.0,
            'unsharp_strength': 1.5,
            'use_log': False
        }
        
        # Stronger Params for 1, 3, 4 (Very dark/low contrast)
        # We switch to LOG Transform for 1 and 3 as requested for major brightness
        if name in ['1', '3']:
            params['use_log'] = True
            params['clahe_clip'] = 8.0 # Extreme local contrast
            params['unsharp_strength'] = 3.0
        elif name == '4':
             params['gamma'] = 0.3
             params['clahe_clip'] = 5.0
             params['unsharp_strength'] = 2.0

        # We will select the BEST result for the report comparison
        # 1. Intensity Adjustment (Gamma OR Log) - This is usually the main enhancement for darkness
        if params['use_log']:
            # Log Transform is better for expanding very low dark values
            best_img = log_transform(img)
            method_name = "Log Transform"
        else:
            gamma_val = params['gamma']
            best_img = adjust_gamma(img, gamma=gamma_val)
            method_name = f"Gamma Correction"
        
        # Save Intensity Comparison
        save_clean_comparison(name, img, best_img, f"{output_dir}/{name}_comparison_final.png")
        
        # Generate the standard plots as well (keeping existing logic)
        cv2.imwrite(f"{output_dir}/{name}_intensity.png", best_img)
        plot_comparison(name, img, best_img, method_name, 
                       f"{output_dir}/{name}_fig_intensity.png")

        # 2. Global Histogram Equalization
        he_img = histogram_equalization(img)
        cv2.imwrite(f"{output_dir}/{name}_he.png", he_img)
        plot_comparison(name, img, he_img, "Global Histogram Equalization", 
                       f"{output_dir}/{name}_fig_he.png")

        # 3. CLAHE (Adaptive Histogram Equalization)
        clip = params['clahe_clip']
        clahe_img = clahe_equalization(img, clip_limit=clip)
        cv2.imwrite(f"{output_dir}/{name}_clahe.png", clahe_img)
        plot_comparison(name, img, clahe_img, f"CLAHE (Clip={clip})", 
                       f"{output_dir}/{name}_fig_clahe.png")

        # Let's use CLAHE for 2 as "Final".
        if name == '2':
             save_clean_comparison(name, img, clahe_img, f"{output_dir}/{name}_comparison_final.png")

        # 4. Arithmetic Operator: Unsharp Masking (Sharpening)
        sigma = params['unsharp_sigma']
        strength = params['unsharp_strength']
        sharp_img = unsharp_mask(img, sigma=sigma, strength=strength)
        cv2.imwrite(f"{output_dir}/{name}_sharpen.png", sharp_img)
        plot_comparison(name, img, sharp_img, f"Unsharp Masking (Str={strength})", 
                       f"{output_dir}/{name}_fig_sharpen.png")

    print(f"Processing complete. Results saved in '{output_dir}'.")

if __name__ == "__main__":
    main()

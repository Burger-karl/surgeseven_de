// static/js/push.js
document.addEventListener('DOMContentLoaded', function() {
    // Check if service workers and push are supported
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        console.log('Service Worker and Push are supported');
        
        // Get VAPID public key from meta tag
        const vapidMeta = document.querySelector('meta[name="vapid-public-key"]');
        let publicKey = vapidMeta ? vapidMeta.getAttribute('content') : '';
        
        // If not found in meta tag, try from window variable (fallback)
        if (!publicKey && window.VAPID_PUBLIC_KEY) {
            publicKey = window.VAPID_PUBLIC_KEY;
        }
        
        // Clean up the key (remove any whitespace or quotes)
        publicKey = publicKey.trim().replace(/"/g, '');
        
        if (!publicKey) {
            console.error('VAPID public key is missing');
            return;
        }
        
        console.log('VAPID Public Key found:', publicKey);
        
        // Register service worker
        navigator.serviceWorker.register('/static/assets/js/serviceworker.js')
            .then(function(registration) {
                console.log('Service Worker registered successfully');
                
                // Request notification permission
                return Notification.requestPermission()
                    .then(function(permission) {
                        if (permission !== 'granted') {
                            console.log('Permission not granted for notifications');
                            return null;
                        }
                        return registration.pushManager.getSubscription();
                    })
                    .then(function(subscription) {
                        if (subscription) {
                            console.log('User is already subscribed');
                            return subscription;
                        }
                        
                        console.log('Subscribing user to push notifications');
                        // Subscribe to push notifications
                        return registration.pushManager.subscribe({
                            userVisibleOnly: true,
                            applicationServerKey: urlBase64ToUint8Array(publicKey)
                        });
                    });
            })
            .then(function(subscription) {
                if (!subscription) {
                    console.log('No subscription (user denied permission)');
                    return;
                }
                
                console.log('Subscription data to send:', JSON.stringify(subscription));
                
                // Send subscription to server
                return fetch('/notify/notifications/push/subscribe/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(subscription)
                });
            })
            .then(function(response) {
                if (response && response.ok) {
                    console.log('Subscription sent to server successfully');
                    return response.json();
                } else if (response) {
                    console.error('Failed to send subscription to server. Status:', response.status);
                    return response.json().then(data => {
                        console.error('Error details:', data);
                        throw new Error('Server responded with error: ' + response.status);
                    });
                }
            })
            .then(function(data) {
                if (data) {
                    console.log('Server response:', data);
                }
            })
            .catch(function(error) {
                console.error('Error in push notification setup:', error);
            });
    } else {
        console.warn('Push messaging is not supported');
    }
});

// Helper function to convert VAPID key
function urlBase64ToUint8Array(base64String) {
    // Remove any whitespace or quotes
    base64String = base64String.trim().replace(/"/g, '');
    
    // Add padding if needed
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');
    
    try {
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    } catch (e) {
        console.error('Error decoding base64:', e);
        throw new Error('Invalid base64 string');
    }
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
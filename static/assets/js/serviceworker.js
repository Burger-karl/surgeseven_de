// // static/js/serviceworker.js
// self.addEventListener('push', function(event) {
//     const data = event.data.json();
//     const title = data.title;
//     const options = {
//         body: data.body,
//         icon: data.icon,
//         badge: data.badge,
//         data: {
//             url: data.url
//         }
//     };
    
//     event.waitUntil(self.registration.showNotification(title, options));
// });

// self.addEventListener('notificationclick', function(event) {
//     event.notification.close();
//     event.waitUntil(clients.openWindow(event.notification.data.url));
// });





// static/js/serviceworker.js
self.addEventListener('push', function(event) {
    let data = {};
    
    try {
        if (event.data) {
            data = event.data.json();
        }
    } catch (e) {
        console.error('Error parsing push data:', e);
        data = {
            title: 'Notification',
            body: 'You have a new notification',
            icon: '/static/assets/img/surge-seven-3.png',
            badge: '/static/assets/img/surge-seven-3.png',
            url: '/'
        };
    }
    
    const title = data.title || 'Notification';
    const options = {
        body: data.body || 'You have a new notification',
        icon: data.icon || '/static/assets/img/surge-seven-3.png',
        badge: data.badge || '/static/assets/img/surge-seven-3.png',
        data: {
            url: data.url || '/'
        }
    };
    
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    
    // This looks to see if the current is already open and focuses if it is
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(function(clientList) {
            if (clientList.length > 0) {
                return clientList[0].focus();
            }
            
            // Open a new window if none is open
            if (clients.openWindow) {
                return clients.openWindow(event.notification.data.url);
            }
        })
    );
});

// Basic service worker installation
self.addEventListener('install', function(event) {
    console.log('Service Worker installing.');
    // Skip waiting to activate immediately
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    console.log('Service Worker activating.');
    // Take control of all pages under this service worker's scope
    event.waitUntil(self.clients.claim());
});
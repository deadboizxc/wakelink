package org.wakelink.android

import android.app.Application
import org.wakelink.android.data.DeviceRepository

class WakeLinkApplication : Application() {
    
    lateinit var deviceRepository: DeviceRepository
        private set
    
    override fun onCreate() {
        super.onCreate()
        
        deviceRepository = DeviceRepository(this)
    }
}
